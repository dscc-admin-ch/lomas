import io
import logging
import os
import re

import opendp as dp
import polars as pl
from opendp._lib import lib_path
from opendp.metrics import metric_distance_type, metric_type
from opendp.mod import enable_features
from opendp_logger import make_load_json

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.models.config import OpenDPConfig
from lomas_core.models.requests import (
    OpenDPQueryModel,
    OpenDPRequestModel,
)
from lomas_core.models.responses import OpenDPPolarsQueryResult, OpenDPQueryResult
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import (
    OPENDP_OUTPUT_MEASURE,
    OPENDP_TYPE_MAPPING,
    OpenDPDatasetInputMetric,
    OpenDPMeasurement,
)
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier


def get_lf_domain(metadata: dict, plan: pl.LazyFrame) -> dp.mod.Domain:
    """
    Returns the OpenDP LazyFrame domain given a metadata dictionary.

    Args:
        metadata (dict): The metadata dictionary
        plan (LazyFrame): The polars query plan as a Polars LazyFrame
    Raises:
        Exception: If there is missing information in the metadata.
    Returns:
        dp.mod.Domain: The OpenDP domain for the metadata.
    """
    series_domains = []
    # Series domains
    for name, series_info in metadata["columns"].items():
        series_bounds = None
        if series_info.type in ["float", "int"]:
            series_type = f"{series_info.type}{series_info.precision}"
            if hasattr(series_info, "lower") and hasattr(series_info, "upper"):
                series_bounds = (series_info.lower, series_info.upper)
        # TODO 392: release opendp 0.12 (adapt with type date)
        elif series_info.type == "datetime":
            series_type = "string"
        else:
            series_type = series_info.type

        if series_type not in OPENDP_TYPE_MAPPING:
            # For valid metadata, only datetime would fail here
            raise InvalidQueryException(
                f"Column type {series_type} not supported by OpenDP. "
                f"Type must be in {OPENDP_TYPE_MAPPING.keys()}"
            )

        series_type = OPENDP_TYPE_MAPPING[series_type]  # type: ignore

        # Note: Same as using option_domain (at least how I understand it)
        series_nullable = "nullable" in series_info

        series_domain = dp.domains.series_domain(
            name,
            dp.domains.atom_domain(T=series_type, nullable=series_nullable, bounds=series_bounds),
        )
        series_domains.append(series_domain)

    # Margins
    # TODO 400: Check lengths vs. keys for public info
    # https://docs.opendp.org/en/stable/getting-started/tabular-data/grouping.html

    # Global margin parameters
    margin_params = get_global_params(metadata)

    # If grouping in the query, we update the margin params
    by_config = extract_group_by_columns(plan.explain())
    if len(by_config) >= 1:
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)

    # TODO 323: Multiple margins?
    # What if two group_by's in one query?
    lf_domain = dp.domains.with_margin(
        dp.domains.lazyframe_domain(series_domains),
        by=by_config,
        public_info="lengths",
        **margin_params,
    )

    return lf_domain


def get_global_params(metadata: dict) -> dict:
    """Get global parameters for margin.

    Args:
        metadata (dict): The metadata dictionary
    Returns:
        dict: Parameters for margin
    """
    margin_params = {}
    margin_params["max_num_partitions"] = 1
    margin_params["max_partition_length"] = metadata["rows"]

    return margin_params


def multiple_group_update_params(metadata: dict, by_config: list, margin_params: dict) -> dict:
    """
    Updates parameters for multiple-column grouping configuration.

    Args:
        metadata (dict): The metadata dictionary.
        by_config (list): List of columns used for grouping.
        margin_params (dict): Current parameters dictionary to update.
    """
    # Initialize max_numpartitions/max_partition_length to 1
    margin_params["max_num_partitions"] = 1
    margin_params["max_partition_length"] = metadata["rows"]

    for column in by_config:
        series_info = metadata["columns"].get(column)

        # max_partitions_length logic:
        # When two columns in the grouping
        # We use as max_partition_length the smaller value
        # at the column level. If None are defined, dataset length is used.

        # Get max_partition_length from series_info, defaulting to metadata["rows"] if not set
        series_max_partition_length = (
            series_info.max_partition_length
            if series_info.max_partition_length is not None
            else metadata["rows"]
        )

        # Update the max_partition_length
        margin_params["max_partition_length"] = min(
            margin_params["max_partition_length"], series_max_partition_length
        )

        # max_num_partitions logic:
        # We multiply the cardinality defined in each column
        # If None are defined, max_num_partitions is equal to None
        if hasattr(series_info, "cardinality"):
            if series_info.cardinality:
                margin_params["max_num_partitions"] *= series_info.cardinality

        # max_influenced_partitions logic:
        # We multiply the max_influenced_partitions defined in each column
        # If None are defined, max_influenced_partitions is equal to None
        if series_info.max_influenced_partitions:
            margin_params["max_influenced_partitions"] = (
                margin_params.get("max_influenced_partitions", 1) * series_info.max_influenced_partitions
            )

        # max_partition_contributions logic:
        # We multiply the max_partition_contributions defined in each column
        # If None are defined, max_partition_contributions is equal to None
        if series_info.max_partition_contributions:
            margin_params["max_partition_contributions"] = (
                margin_params.get("max_partition_contributions", 1) * series_info.max_partition_contributions
            )

    # If max_influenced_partitions > max_ids:
    # Then max_influenced_partitions = max_ids
    if "max_influenced_partitions" in margin_params:
        margin_params["max_influenced_partitions"] = min(
            metadata["max_ids"], margin_params["max_influenced_partitions"]
        )

    # If max_partition_contributions > max_ids:
    # Then max_partition_contributions = max_ids
    if "max_partition_contributions" in margin_params:
        margin_params["max_partition_contributions"] = min(
            metadata["max_ids"],
            margin_params.get("max_partition_contributions"),
        )
    return margin_params


class OpenDPQuerier(DPQuerier[OpenDPRequestModel, OpenDPQueryModel, OpenDPQueryResult]):
    """Concrete implementation of the DPQuerier ABC for the OpenDP library."""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: AdminDatabase,
    ) -> None:
        """Initializer.

        Args:
            data_connector (DataConnector): DataConnector for the dataset
                to query.
        """
        super().__init__(data_connector, admin_database)

        # Get metadata once and for all
        self.metadata = dict(self.data_connector.get_metadata())

    def cost(self, query_json: OpenDPRequestModel) -> tuple[float, float]:
        """
        Estimate cost of query.

        Args:
            query_json (OpenDPRequestModel): The request model object.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InternalServerException: For any other unforseen exceptions.
            InvalidQueryException: The pipeline does not contain a
                "measurement", there is not enough budget or the dataset
                does not exist.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        opendp_pipe = reconstruct_measurement_pipeline(query_json, self.metadata)

        measurement_type = get_output_measure(opendp_pipe)
        # https://docs.opendp.org/en/stable/user/combinators.html#measure-casting
        if measurement_type == OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE:
            opendp_pipe = dp.combinators.make_zCDP_to_approxDP(opendp_pipe)
            measurement_type = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE

        max_ids = self.metadata["max_ids"]
        try:
            # d_in is int as input metric is a dataset metric
            cost = opendp_pipe.map(d_in=int(max_ids))
        except Exception as e:
            logging.exception(e)
            raise ExternalLibraryException(DPLibraries.OPENDP, "Error obtaining cost:" + str(e)) from e

        # Cost interpretation
        match measurement_type:
            case OpenDPMeasurement.FIXED_SMOOTHED_MAX_DIVERGENCE:  # Approximate DP with fix delta
                epsilon, delta = cost
            case OpenDPMeasurement.MAX_DIVERGENCE:  # Pure DP
                epsilon, delta = cost, 0
            case OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE:  # Approximate DP
                if query_json.fixed_delta is None:
                    raise InvalidQueryException(
                        "fixed_delta must be set for smooth max divergence"
                        + " and zero concentrated divergence."
                    )
                epsilon = cost.epsilon(delta=query_json.fixed_delta)
                delta = query_json.fixed_delta
            case _:
                raise InternalServerException(f"Invalid measurement type: {measurement_type}")

        return epsilon, delta

    def query(self, query_json: OpenDPQueryModel) -> OpenDPQueryResult | OpenDPPolarsQueryResult:
        """Perform the query and return the response.

        Args:
            query_json (OpenDPQueryModel): The input model for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            (Union[List, int, float]) query result
        """
        opendp_pipe = reconstruct_measurement_pipeline(query_json, self.metadata)

        if query_json.pipeline_type == "legacy":
            input_data = self.data_connector.get_pandas_df().to_csv(header=False, index=False)
        elif query_json.pipeline_type == "polars":
            input_data = self.data_connector.get_polars_lf()
        else:  # TODO 401 validate input in json model instead of with if-else statements
            raise InternalServerException(
                f"""Invalid pipeline type: '{query_json.pipeline_type}.'
                                        Should be legacy or polars"""
            )

        try:
            release_data = opendp_pipe(input_data)
        except Exception as e:
            logging.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP,
                "Error executing query:" + str(e),
            ) from e

        if isinstance(release_data, dp.extras.polars.OnceFrame):
            release_data = release_data.collect()
            return OpenDPPolarsQueryResult(value=release_data)
        return OpenDPQueryResult(value=release_data)


def is_measurement(pipeline: dp.Measurement) -> None:
    """Check if the pipeline is a measurement.

    Args:
        pipeline (dp.Measurement): The measurement to check.

    Raises:
        InvalidQueryException: If the pipeline is not a measurement.
    """
    if not isinstance(pipeline, dp.Measurement):
        e = "The pipeline provided is not a measurement. It cannot be processed in this server."
        logging.exception(e)
        raise InvalidQueryException(e)


def has_dataset_input_metric(pipeline: dp.Measurement) -> None:
    """Check that the input metric of the pipeline is a dataset metric.

    Args:
        pipeline (dp.Measurement): The pipeline to check.

    Raises:
        InvalidQueryException: If the pipeline input metric is not
                                a dataset input metric.
    """
    distance_type = metric_distance_type(pipeline.input_metric)
    if not distance_type == OpenDPDatasetInputMetric.INT_DISTANCE:
        e = (
            f"The input distance type is not {OpenDPDatasetInputMetric.INT_DISTANCE}"
            + f" but {distance_type} which is not a valid distance type for datasets."
            + " It cannot be processed in this server."
        )
        logging.exception(e)
        raise InvalidQueryException(e)

    dataset_input_metric = [m.value for m in OpenDPDatasetInputMetric]
    if not metric_type(pipeline.input_metric) in dataset_input_metric:
        e = (
            f"The input distance metric {pipeline.input_metric} is not a dataset"
            + " input metric. It cannot be processed in this server."
        )
        logging.exception(e)
        raise InvalidQueryException(e)


def extract_group_by_columns(plan: str) -> list:
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
    match = re.findall(aggregate_by_pattern, plan)

    if len(match) == 1:
        # Extract the columns part
        columns_part = match[0]
        # Find all column names inside col("...")
        column_names = re.findall(r'col\("([^"]+)"\)', columns_part)
        return column_names
    if len(match) > 1:
        raise InvalidQueryException(
            "Your are trying to do multiple groupings. "
            "This is currently not supported, please use one grouping"
        )
    return []


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
    # Reconstruct pipeline
    if query_json.pipeline_type == "legacy":
        opendp_pipe = make_load_json(query_json.opendp_json)
    elif query_json.pipeline_type == "polars":
        plan = pl.LazyFrame.deserialize(io.StringIO(query_json.opendp_json), format="json")

        assert query_json.mechanism is not None
        output_measure = OPENDP_OUTPUT_MEASURE[query_json.mechanism]

        lf_domain = get_lf_domain(metadata, plan)

        opendp_pipe = dp.measurements.make_private_lazyframe(
            lf_domain, dp.metrics.symmetric_distance(), output_measure, plan
        )
    else:
        raise InternalServerException(f"Unsupported OpenDP pipeline type: {query_json.pipeline_type}")

    # Verify that the pipeline is safe and valid
    is_measurement(opendp_pipe)
    has_dataset_input_metric(opendp_pipe)

    return opendp_pipe


def get_output_measure(opendp_pipe: dp.Measurement) -> str:
    """Get output measure type.

    Args:
        opendp_pipe (dp.Measurement): Pipeline to get measure type.

    Raises:
        InternalServerException: If the measure type is unknown.

    Returns:
        str: One of :py:class:`OpenDPMeasurement`.
    """
    output_type = opendp_pipe.output_distance_type
    output_measure = opendp_pipe.output_measure

    if not isinstance(output_type, str):
        if output_type.origin in ["SMDCurve", "Tuple"]:  # TODO 360 : constant.
            output_type = output_type.args[0]
        else:
            raise InternalServerException(
                f"Cannot process output measure: {output_measure} with output type {output_type}."
            )

    if output_measure == dp.measures.fixed_smoothed_max_divergence():
        measurement = OpenDPMeasurement.FIXED_SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.max_divergence():
        measurement = OpenDPMeasurement.MAX_DIVERGENCE
    elif output_measure == dp.measures.smoothed_max_divergence():
        measurement = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.zero_concentrated_divergence():
        measurement = OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE
    else:
        raise InternalServerException(f"Unknown type of output measure divergence: {output_measure}")
    return measurement


def set_opendp_features_config(opendp_config: OpenDPConfig):
    """Enable opendp features based on config.

    See https://github.com/opendp/opendp/discussions/304

    Also sets the "OPENDP_POLARS_LIB_PATH" environment variable
    for correctly creating private lazyframes from deserialized
    polars plans.

    Args:
        opendp_config (OpenDPConfig): OpenDP configurations
    """
    if opendp_config.contrib:
        enable_features("contrib")

    if opendp_config.floating_point:
        enable_features("floating-point")

    if opendp_config.honest_but_curious:
        enable_features("honest-but-curious")

    # Set DP Libraries config
    os.environ["OPENDP_LIB_PATH"] = str(lib_path)
