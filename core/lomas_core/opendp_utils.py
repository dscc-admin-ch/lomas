import io
import re
from base64 import b64decode
from functools import reduce

import opendp.prelude as dp
import polars as pl

from lomas_core.constants import OPENDP_OUTPUT_MEASURE, OPENDP_TYPE_MAPPING, OpenDpPipelineType
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
        if series_info["type"] in [MetadataColumnType.FLOAT, MetadataColumnType.INT]:
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


def reconstruct_measurement_pipeline(query_json: OpenDPQueryModel, metadata: dict) -> dp.Measurement:
    """Reconstruct OpenDP pipeline from json representation.

    Args:
        query_json (BaseModel): The JSON request object for the query.
        metadata (dict): The dataset metadata dictionary.\
            Only used for polars pipelines.

    Raises:
        InvalidQueryException: If the pipeline is not a measurement or\
            the pipeline type is not supported.

    Returns:
        dp.Measurement: The reconstructed pipeline.
    """
    dp.enable_features("contrib")
    # Reconstruct pipeline
    if query_json.pipeline_type == OpenDpPipelineType.POLARS:
        plan = pl.LazyFrame.deserialize(io.BytesIO(b64decode(query_json.opendp_json.encode("utf-8"))))

        assert query_json.mechanism is not None
        output_measure = OPENDP_OUTPUT_MEASURE[query_json.mechanism]

        lf_domain = get_lf_domain(metadata, plan)

        opendp_pipe = dp.m.make_private_lazyframe(
            lf_domain,
            dp.symmetric_distance(),
            output_measure,
            plan,
            threshold=100,
        )
    else:
        raise InternalServerException(f"Unsupported OpenDP pipeline type: {query_json.pipeline_type}")

    return opendp_pipe
