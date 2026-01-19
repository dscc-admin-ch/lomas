import re
from base64 import b64decode
from functools import reduce

import opendp.prelude as dp
import polars as pl

from lomas_core.constants import OPENDP_TYPE_MAPPING, OpenDpPipelineType
from lomas_core.error_handler import InternalServerException, InvalidQueryException
from lomas_core.models.constants import MetadataColumnType
from lomas_core.models.requests import OpenDPQueryModel


def get_raw_lf_domain(metadata_dict: dict) -> dp.Domain:
    """
    Builds the "raw" lf domain from the metadata.

    The domain in considered "raw" because it does not contain any margin.
    The domain is built by putting together series domains from each column.
    """
    series_domains = []
    # Series domains
    for name, series_info in metadata_dict["columns"].items():
        series_bounds = None
        if series_info["type"] in {MetadataColumnType.FLOAT, MetadataColumnType.INT}:
            series_type = f"{series_info['type']}{series_info['precision']}"
            if "lower" in series_info and "upper" in series_info:
                series_bounds = (series_info["lower"], series_info["upper"])
        # TODO 392: release opendp 0.12 (adapt with type date)
        elif series_info["type"] == MetadataColumnType.DATETIME:
            series_type = MetadataColumnType.STRING
        else:
            series_type = series_info["type"]

        if series_type not in OPENDP_TYPE_MAPPING:
            # For valid metadata, only datetime would fail here
            raise InvalidQueryException(
                f"Column type {series_type} not supported by OpenDP. "
                f"Type must be in {OPENDP_TYPE_MAPPING.keys()}"
            )

        # Note: Same as using option_domain (at least how I understand it)
        series_nullable = (
            series_info["nullable_proportion"] > 0.0 and series_type != MetadataColumnType.STRING
        )
        series_type = OPENDP_TYPE_MAPPING[series_type]

        series_domain = dp.series_domain(
            name,
            dp.atom_domain(T=series_type, nan=series_nullable, bounds=series_bounds),
        )
        series_domains.append(series_domain)

    # Build domain from series domain
    raw_lf_domain = dp.lazyframe_domain(series_domains)

    return raw_lf_domain


def add_global_margin(lf_domain: dp.Domain, metadata: dict) -> dp.Domain:
    """Builds the "global" (by = []) margin from the metadata."""
    margin = dp.polars.Margin(max_length=metadata["rows"], invariant="keys")
    lf_domain = dp.with_margin(lf_domain, margin)
    return lf_domain


def extract_group_by_columns(plan: pl.LazyFrame) -> list:
    """
    Extract column names used in the BY operation from the plan string.

    Parameters:
    plan (str): The polars query plan as a string.
    Returns:
    list: A list of column names used in the BY operation.
    """
    # Regular expression to capture the content inside BY []
    aggregate_by_pattern = r"AGGREGATE(?:.|\n)+?BY \[(.*?)\]"

    # Find the part of the plan related to the GROUP BY clause
    match re.findall(aggregate_by_pattern, plan.explain()):
        case []:
            return []
        case [columns_part]:
            # Find all column names inside col("...")
            column_names = re.findall(r'col\("([^"]+)"\)', columns_part)
            return column_names
        case _:
            raise InvalidQueryException(
                "Your are trying to do multiple groupings. "
                "This is currently not supported, please use one grouping"
            )


def multiply_or_none(values: list[int | None]) -> int | None:
    """
    Multiply all values in the list, return None if any value is None.

    Args:
        values (list[Optional[int]]): A list of int or None

    Returns:
        None if any None in the list, multiplied values of list otherwise.
    """
    if any(v is None for v in values):
        return None

    return reduce(lambda acc, v: acc * v, values, 1)  # type: ignore[operator]


def multiple_group_params(metadata: dict, by_config: list) -> dict:
    """
    Updates parameters for multiple-column grouping configuration.

    Args:
        metadata (dict): The metadata dictionary.
        by_config (list): List of columns used for grouping.

    Returns:
        (dict) updated margin_params for the groupby
    """
    # Initialize values
    max_length = metadata["rows"]
    max_num_partitions_l = []
    max_influenced_partitions_l = []
    max_partition_contributions_l = []

    # Iterate through grouping columns
    for column in by_config:
        series_info = metadata["columns"][column]

        # Update the max_length
        if (series_max_length := series_info.get("max_partition_length")) is not None:
            max_length = min(max_length, series_max_length)

        # Get all groupby parameters in a list
        max_num_partitions_l.append(series_info.get("cardinality", None))
        max_influenced_partitions_l.append(series_info.get("max_influenced_partitions", None))
        max_partition_contributions_l.append(series_info.get("max_partition_contributions", None))

    # We multiply the cardinality, max_influenced_partitions and max_partition_contributions
    # of each groupby column. If any None, then no margin.
    max_num_partitions = multiply_or_none(max_num_partitions_l)
    max_influenced_partitions = multiply_or_none(max_influenced_partitions_l)
    max_partition_contributions = multiply_or_none(max_partition_contributions_l)

    # Make margin
    margin_params = {}
    margin_params["max_length"] = max_length
    if max_num_partitions:
        margin_params["max_groups"] = max_num_partitions

    # If max_influenced_partitions > max_ids: then max_influenced_partitions = max_ids
    if max_influenced_partitions:
        max_influenced_partitions = min(metadata["max_ids"], max_influenced_partitions)
        margin_params["max_influenced_partitions"] = max_influenced_partitions

    # If max_partition_contributions > max_ids: then max_partition_contributions = max_ids
    if max_partition_contributions:
        max_partition_contributions = min(metadata["max_ids"], max_partition_contributions)
        margin_params["max_partition_contributions"] = max_partition_contributions

    return margin_params


def get_lf_domain(metadata_dict: dict, plan: pl.LazyFrame) -> dp.Domain:
    """
    Returns the OpenDP LazyFrame domain given a metadata dictionary.

    Args:
        metadata_dict (dict): The metadata dictionary
        plan (LazyFrame): The polars query plan as a Polars LazyFrame
    Raises:
        Exception: If there is missing information in the metadata.
    Returns:
        dp.Domain: The OpenDP domain for the metadata.
    """
    # Get raw lf domain (without margins)
    raw_lf_domain = get_raw_lf_domain(metadata_dict)

    # Add global margin to domain (for by=[])
    lf_domain = add_global_margin(raw_lf_domain, metadata_dict)

    # If grouping in the query, we update the margin params
    by_config = extract_group_by_columns(plan)
    if len(by_config) >= 1:
        margin_params = multiple_group_params(metadata_dict, by_config)
        # TODO 323: Multiple margins?
        # What if two group_by's in one query?
        # Update margin with group_margin
        margin = dp.polars.Margin(by=by_config, **margin_params, invariant="keys")
        lf_domain = dp.with_margin(lf_domain, margin)
    return lf_domain


import itertools

import opendp.prelude as dp


def build_margins_from_metadata(metadata: dict):
    """
    Build OpenDP Polars margins from dataset metadata,
    including all multi-column grouping margins.
    """
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

    # For now, no more than 5 combination
    for r in range(2, min(len(column_names) + 1, 6)):
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


def deserialize_context_query(query_json: OpenDPQueryModel, metadata: dict, input_data):
    """TODO"""
    dp.enable_features("contrib")
    # Reconstruct pipeline
    if query_json.pipeline_type == OpenDpPipelineType.POLARS:
        # not given like this by the user, depends on the parameter
        # rho or epsilon is used
        # assert query_json.mechanism is not None

        # Context
        # TODO: create context based on user choices and with margin
        # new_context = create_context_with_margin(...)
        margins = build_margins_from_metadata(metadata=metadata)

        new_context = dp.Context.compositor(
            data=input_data,
            privacy_unit=dp.unit_of(contributions=metadata["max_ids"]),
            privacy_loss=dp.loss_of(
                epsilon=100,  # TODO: query_json.fixed_epsilon,
                delta=query_json.fixed_delta,
            ),
            split_evenly_over=1,  # fixed to 1 for now, spend whole budget sent by user
            margins=margins,
        )
        serialized_plan = b64decode(query_json.opendp_json.encode("utf-8"))
        polars_plan = new_context.deserialize_polars_plan(serialized_plan)
    else:
        raise InternalServerException(f"Unsupported OpenDP pipeline type: {query_json.pipeline_type}")

    return polars_plan


def reconstruct_measurement_pipeline():
    pass
