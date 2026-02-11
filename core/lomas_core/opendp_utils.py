import itertools
from base64 import b64decode
from typing import Any

import opendp.prelude as dp
import polars as pl

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import Metadata
from lomas_core.models.requests import GetDummyContext, OpenDPQueryModel

dp.enable_features("contrib")


def build_margins_from_metadata(metadata: Metadata) -> list:
    """
    Build a list of Polars margins from dataset metadata.

    This function derives margin constraints at three levels:
    1. A global margin based on the total number of rows.
    2. Single-column margins using per-column partition length and cardinality.
    3. Multi-column grouping margins (up to 4 columns) by combining individual
       column constraints.

    Args:
        metadata (Metadata): The metadata model for the real dataset.

    Raises:
        ValueError:
            If the metadata does not define the total number of rows.

    Returns:
        list: A list of ``dp.polars.Margin`` objects encoding global, per-column,
            and multi-column grouping constraints inferred from the metadata.
    """
    margins = []
    # --------------------
    # Global margin
    # --------------------
    rows = metadata.rows
    if rows is None:
        raise ValueError("Metadata must contain 'rows'")

    # TODO: invariant should change depending of the metadata (nrows given or not)
    # TBD with new metadata structure
    margins.append(dp.polars.Margin(max_length=rows, invariant="lengths"))

    # --------------------
    # Column-level margins
    # --------------------
    columns = metadata.columns

    # Store constraints for grouping
    grouping_constraints = {}

    for column_name, col_meta in columns.items():
        max_partition_length = col_meta.max_partition_length
        cardinality = getattr(col_meta, "cardinality", None)

        by = [column_name]

        # Save constraints for later grouping
        grouping_constraints[column_name] = {
            "max_partition_length": max_partition_length,
            "cardinality": cardinality,
        }

        # Categorical columns
        margin_kwargs: dict[str, Any] = {
            "by": by,
            "invariant": "keys",
        }

        if max_partition_length is not None:
            margin_kwargs["max_length"] = max_partition_length

        if cardinality is not None:
            margin_kwargs["max_groups"] = cardinality

        margins.append(dp.polars.Margin(**margin_kwargs))

    # --------------------
    # Multi-column groupings
    # --------------------
    column_names = list(grouping_constraints.keys())

    # For now, no more than 4 combination
    for r in range(2, min(len(column_names) + 1, 5)):
        for combo in itertools.combinations(column_names, r):
            max_lengths = []
            max_groups = []

            for col in combo:
                c = grouping_constraints[col]

                if c["max_partition_length"] is not None:
                    max_lengths.append(c["max_partition_length"])

                if c["cardinality"] is not None:
                    max_groups.append(c["cardinality"])

            margin_kwargs = {
                "by": list(combo),
                "invariant": "keys",
            }

            # min(max_partition_length)
            max_lengths = [
                grouping_constraints[col]["max_partition_length"]
                for col in combo
                if grouping_constraints[col]["max_partition_length"] is not None
            ]

            if max_lengths:
                margin_kwargs["max_length"] = min(max_lengths)

            # max_groups logic: multiply max_groups of all columns from combo
            # If one group is None and other is not, we keep the max group from the other
            # if all none, max_groups is none.
            cardinalities = [
                grouping_constraints[col]["cardinality"]
                for col in combo
                if grouping_constraints[col]["cardinality"] is not None
            ]
            if all(c is not None for c in cardinalities):
                product = 1
                for c in cardinalities:  # type: ignore[assignment]
                    product *= c  # type: ignore[operator]
                margin_kwargs["max_groups"] = product

            margins.append(dp.polars.Margin(**margin_kwargs))

    return margins


def build_context(
    query_json: GetDummyContext, metadata: Metadata, margins: list, input_data: pl.LazyFrame
) -> dp.Context:
    """
    Construct a differential privacy context from query parameters and metadata.

    This function validates the provided privacy parameters and builds a
    ``dp.Context`` using either a Laplace (epsilon-based) or Gaussian (rho-based)
    privacy loss, depending on the input. Exactly one of ``epsilon`` or ``rho``
    must be specified.

    The context is created using a compositor with a fixed privacy budget split
    (currently set to 1) and the margins derived from the dataset metadata.

    Args:
        query_json (GetDummyContext): Request defining the privacy parameters, including \
            ``epsilon``, ``rho``, and optional ``delta``.
        metadata (Metadata): The metadata model for the real dataset.
        margins (list): List of ``dp.polars.Margin`` objects defining aggregation and\
            grouping constraints.
        input_data (pl.LazyFrame): Input dataset on which the differentially private context \
            will be applied.

    Raises:
        InternalServerException:
            If both ``epsilon`` and ``rho`` are provided.
        InternalServerException:
            If neither ``epsilon`` nor ``rho`` is provided.

    Returns:
        dp.Context: A dp context configured with\
            the requested privacy loss, margins, and input data.
    """
    epsilon = query_json.epsilon
    rho = query_json.rho
    delta = query_json.delta

    if epsilon is not None and rho is not None:
        raise InternalServerException("Provide only one of epsilon or rho, not both.")

    if epsilon is None and rho is None:
        raise InternalServerException("One of epsilon or rho must be provided.")

    if epsilon:
        # Laplace
        return dp.Context.compositor(
            data=input_data,
            privacy_unit=dp.unit_of(contributions=metadata.max_ids),
            privacy_loss=dp.loss_of(
                epsilon=epsilon,
                delta=delta,
            ),
            split_evenly_over=1,  # fixed to 1 for now, spend whole budget sent by user
            margins=margins,
        )

    # Gaussian
    return dp.Context.compositor(
        data=input_data,
        privacy_unit=dp.unit_of(contributions=metadata.max_ids),
        privacy_loss=dp.loss_of(
            rho=rho,
            delta=delta,
        ),
        split_evenly_over=1,
        margins=margins,
    )


def deserialize_context_query(
    query_json: OpenDPQueryModel, metadata: Metadata, input_data: pl.LazyFrame, context_only: bool = False
) -> dp.polars.LazyFrameQuery | dp.Context:
    """
    Build a differential privacy context and optionally deserialize a Polars query plan.

    Args:
        query_json (OpenDPQueryModel): Query containing privacy parameters and \
            a serialized OpenDP Polars query plan.
        metadata (Metadata): The metadata model for the real dataset.

        input_data (pl.LazyFrame): Input dataset.
        context_only (bool, optional): If ``True``, return only the constructed ``dp.Context`` \
            without deserializing the query plan.
            Defaults to ``False``.

    Returns:
        dp.polars.LazyFrameQuery | dp.Context: The constructed ``dp.Context`` if ``context_only`` \
            is ``True``; otherwise, a deserialized ``dp.polars.LazyFrameQuery`` bound to the\
            new context.
    """
    # Extract margins from metadata
    margins = build_margins_from_metadata(metadata=metadata)

    # Create new context based on dummy/real data
    new_context = build_context(query_json, metadata, margins, input_data)

    if context_only:
        return new_context

    # Serialize plan given by user
    serialized_plan = b64decode(query_json.opendp_json.encode("utf-8"))

    # Apply and deserialize polars plan with new context
    polars_plan = new_context.deserialize_polars_plan(serialized_plan)

    return polars_plan
