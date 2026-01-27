import itertools
from base64 import b64decode

import opendp.prelude as dp
import polars as pl

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import Metadata
from lomas_core.models.requests import GetDummyContext, OpenDPQueryModel

dp.enable_features("contrib")


def build_margins_from_metadata(metadata: Metadata) -> list:
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
        margin_kwargs = {
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
                for c in cardinalities:
                    product *= c
                margin_kwargs["max_groups"] = product

            margins.append(dp.polars.Margin(**margin_kwargs))

    return margins


def build_context(
    query_json: GetDummyContext, metadata: Metadata, margins: list, input_data: pl.LazyFrame
) -> dp.Context:
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
    query_json: OpenDPQueryModel, metadata: Metadata, input_data: pl.LazyFrame
) -> dp.polars.LazyFrameQuery:
    """TODO"""
    # Extract margins from metadata
    margins = build_margins_from_metadata(metadata=metadata)

    # Create new context based on dummy/real data
    new_context = build_context(query_json, metadata, margins, input_data)

    # Serialize plan given by user
    serialized_plan = b64decode(query_json.opendp_json.encode("utf-8"))

    # Apply and deserialize polars plan with new context
    polars_plan = new_context.deserialize_polars_plan(serialized_plan)

    return polars_plan
