import itertools
from base64 import b64decode

import opendp.prelude as dp

from lomas_core.error_handler import InternalServerException
from lomas_core.models.requests import OpenDPQueryModel


def build_margins_from_metadata(metadata: dict) -> list:
    margins = []
    # --------------------
    # Global margin
    # --------------------

    rows = metadata.get("rows")
    if rows is None:
        raise ValueError("Metadata must contain 'rows'")

    margins.append(dp.polars.Margin(max_length=rows))

    # --------------------
    # Column-level margins
    # --------------------
    columns = metadata.get("columns", {})

    # Store constraints for grouping
    grouping_constraints = {}

    for column_name, col_meta in columns.items():
        col_type = col_meta.get("type")
        max_partition_length = col_meta.get("max_partition_length")
        cardinality = col_meta.get("cardinality")

        by = [column_name]

        # Save constraints for later grouping
        grouping_constraints[column_name] = {
            "max_partition_length": max_partition_length,
            "cardinality": cardinality,
        }

        # Categorical columns
        if col_type == "categorical":
            margin_kwargs = {
                "by": by,
                "invariant": "keys",
            }

            if max_partition_length is not None:
                margin_kwargs["max_length"] = max_partition_length

            if cardinality is not None:
                margin_kwargs["max_groups"] = cardinality

            margins.append(dp.polars.Margin(**margin_kwargs))
            continue

        # String columns
        if col_type == "string":
            margin_kwargs = {
                "by": by,
                "invariant": "keys",
            }

            if max_partition_length is not None:
                margin_kwargs["max_length"] = max_partition_length

            margins.append(dp.polars.Margin(**margin_kwargs))
            continue

        # Other
        margins.append(
            dp.polars.Margin(
                by=by,
                invariant="keys",
            )
        )

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
            if max_lengths:
                margin_kwargs["max_length"] = min(max_lengths)

            # max_groups: None if ANY cardinality is None
            cardinalities = [grouping_constraints[col]["cardinality"] for col in combo]

            if all(c is not None for c in cardinalities):
                product = 1
                for c in cardinalities:
                    product *= c
                margin_kwargs["max_groups"] = product

            margins.append(dp.polars.Margin(**margin_kwargs))

    return margins


def build_context(query_json: OpenDPQueryModel, metadata: dict, margins: list, input_data) -> dp.Context:
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
            privacy_unit=dp.unit_of(contributions=metadata["max_ids"]),
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
        privacy_unit=dp.unit_of(contributions=metadata["max_ids"]),
        privacy_loss=dp.loss_of(
            rho=rho,
            delta=delta,
        ),
        split_evenly_over=1,
        margins=margins,
    )


def deserialize_context_query(query_json: OpenDPQueryModel, metadata: dict, input_data):
    """TODO"""
    dp.enable_features("contrib")
    # Extract margins from metadata
    margins = build_margins_from_metadata(metadata=metadata)

    # Create new context based on dummy/real data
    new_context = build_context(query_json, metadata, margins, input_data)

    # Serialize plan given by user
    serialized_plan = b64decode(query_json.opendp_json.encode("utf-8"))

    # Apply and deserialize polars plan with new context
    polars_plan = new_context.deserialize_polars_plan(serialized_plan)

    return polars_plan
