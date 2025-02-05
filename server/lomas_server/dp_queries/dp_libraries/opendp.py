import logging
import io
import os
import re

import opendp as dp
import polars as pl
from opendp._lib import lib_path
from opendp.metrics import metric_distance_type, metric_type
from opendp.mod import enable_features
from opendp_logger import make_load_json
from data_connector.data_connector import DataConnector

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
from lomas_core.models.responses import OpenDPQueryResult
from lomas_server.constants import OpenDPDatasetInputMetric, OpenDPMeasurement
from lomas_server.dp_queries.dp_querier import DPQuerier


def get_lf_domain(metadata, by_config):
    """
    Returns the OpenDP LazyFrame domain given a metadata dictionary.
    Args:
        metadata (dict): The metadata dictionary
        by_config (list): Configuration for grouping.
    Raises:
        Exception: If there is missing information in the metadata.
    Returns:
        dp.mod.Domain: The OpenDP domain for the metadata.
    """
    series_domains = []
    # Series domains
    for name, series_info in metadata["columns"].items():
        if series_info["type"] in ["float", "int"]:
            series_type = f"{series_info['type']}{series_info['precision']}"
        # TODO: release opendp 0.12 (adapt with type date)
        elif series_info["type"] == "datetime":
            series_type = "string"
        else:
            series_type = series_info["type"]

        # TODO should this be a constant? leave here
        opendp_type_mapping = {
            "int32": dp.typing.i32,
            "float32": dp.typing.f32,
            "int64": dp.typing.i64,
            "float64": dp.typing.f64,
            "string": dp.typing.String,
            "boolean": bool,
        }

        if series_type not in opendp_type_mapping:
            # For valid metadata, only datetime would fail here
            raise InvalidQueryException(
                f"Column type {series_type} not supported by OpenDP. "
                f"Type must be in {opendp_type_mapping.keys()}"
            )

        series_type = opendp_type_mapping[series_type]

        # Note: Same as using option_domain (at least how I understand it)
        series_nullable = "nullable" in series_info

        series_bounds = None
        if "lower" in series_info and "upper" in series_info:
            series_bounds = (series_info["lower"], series_info["upper"])

        series_domain = dp.domains.series_domain(
            name,
            dp.domains.atom_domain(
                T=series_type, nullable=series_nullable, bounds=series_bounds
            ),
        )
        series_domains.append(series_domain)

    # Margins
    # TODO Check lengths vs. keys for public info -> not in doc anymore.

    # Global margin parameters
    margin_params = get_global_params(metadata)

    # If grouping in the query, we update the margin params
    if by_config:
        margin_params = update_params_by_grouping(
            metadata, by_config, margin_params
        )
    else:
        by_config = []

    # TODO: Multiple margins?
    # What if two group_by's in one query?
    lf_domain = dp.domains.with_margin(
        dp.domains.lazyframe_domain(series_domains),
        by=by_config,
        public_info="lengths",
        **margin_params,
    )

    return lf_domain


def get_global_params(metadata):
    """Get global parameters for margin
    Args:
        metadata (dict): The metadata dictionary
    Returns:
        dict: Parameters for margin
    """
    margin_params = {}
    margin_params["max_num_partitions"] = 1
    margin_params["max_partition_length"] = metadata["rows"]

    return margin_params


def update_params_by_grouping(metadata, by_config, margin_params):
    """
    Updates the parameters for margin adaptation based on
    grouping configuration.
    Args:
        metadata (dict): The metadata dictionary.
        by_config (list): Configuration for grouping.
        margin_params (dict): Current parameters dictionary to update.
    Returns:
        dict: Updated parameters dictionary.
    """
    if len(by_config) == 1:
        series_info = metadata["columns"].get(by_config[0])
        single_group_update_params(metadata, series_info, margin_params)
    else:
        multiple_group_update_params(metadata, by_config, margin_params)
    return margin_params


def single_group_update_params(metadata, series_info, margin_params):
    """
    Updates parameters for single-column grouping configuration.
    Args:
        metadata (dict): The metadata dictionary.
        series_info (dict): Metadata for the series (column).
        params (dict): Current parameters dictionary to update.
    """
    # Max_partition_length logic:
    # Must be specified at least at the dataset level (global)
    # if none are specified at the partition, we use the global
    margin_params["max_partition_length"] = min(
        metadata["rows"],
        series_info.get("max_partition_length", metadata["rows"]),
    )

    # If none is given for the partition, None is used (allowed)
    margin_params["max_num_partitions"] = series_info.get("cardinality")

    # max_influenced partitions logic:
    # "Greatest number of partitions any one
    # individual may contribute to."
    # If max_influenced_partitions is bigger than max_ids
    # we fix it at max_ids (should not happen)
    if "max_influenced_partitions" in series_info:
        margin_params["max_influenced_partitions"] = min(
            metadata["max_ids"],
            series_info.get("max_influenced_partitions"),
        )
    # max_influenced partitins logic:
    # "The greatest number of records an individual
    # may contribute to any one partition."
    # If max_influenced_partitions is bigger than max_ids
    # we fix it at max_ids (should not happen)
    if "max_partition_contributions" in series_info:
        margin_params["max_partition_contributions"] = min(
            metadata["max_ids"],
            series_info.get("max_partition_contributions"),
        )


def multiple_group_update_params(metadata, by_config, margin_params):
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
        margin_params["max_partition_length"] = min(
            margin_params["max_partition_length"],
            series_info.get("max_partition_length", metadata["rows"]),
        )

        # max_partitions_length logic:
        # We multiply the cardinality defined in each column
        # If None are defined, max_num_partitions is equal to None
        if "cardinality" in series_info:
            margin_params["max_num_partitions"] *= series_info.get(
                "cardinality"
            )

        # max_influenced_partitions logic:
        # We multiply the max_influenced_partitions defined in each column
        # If None are defined, max_influenced_partitions is equal to None
        if "max_influenced_partitions" in series_info:
            margin_params["max_influenced_partitions"] = (
                margin_params.get("max_influenced_partitions", 1)
                * series_info["max_influenced_partitions"]
            )

        # max_partition_contributions logic:
        # We multiply the max_partition_contributions defined in each column
        # If None are defined, max_partition_contributions is equal to None
        if "max_partition_contributions" in series_info:
            margin_params["max_partition_contributions"] = (
                margin_params.get("max_partition_contributions", 1)
                * series_info["max_partition_contributions"]
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

class OpenDPQuerier(DPQuerier[OpenDPRequestModel, OpenDPQueryModel, OpenDPQueryResult]):
    """Concrete implementation of the DPQuerier ABC for the OpenDP library."""
    
    def __init__(
        self,
        data_connector: DataConnector,
    ) -> None:
        """Initializer.
        Args:
            data_connector (DataConnector): DataConnector for the dataset
                to query.
        """
        super().__init__(data_connector)

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
        opendp_pipe = reconstruct_measurement_pipeline(
            query_json, self.metadata
        )

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

    def query(self, query_json: OpenDPQueryModel) -> OpenDPQueryResult:
        """Perform the query and return the response.

        Args:
            query_json (OpenDPQueryModel): The input model for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            (Union[List, int, float]) query result
        """
        opendp_pipe = reconstruct_measurement_pipeline(
            query_json, self.metadata
        )

        if query_json.pipeline_type == "legacy":
            input_data = self.data_connector.get_pandas_df().to_csv(
                header=False, index=False
            )
        elif query_json.pipeline_type == "polars":
            input_data = self.data_connector.get_polars_lf()
        else:  # TODO validate input in json model instead of with if-else statements
            raise InvalidQueryException("invalid pipeline type")


        try:
            release_data = opendp_pipe(input_data)
        except Exception as e:
            logging.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP,
                "Error executing query:" + str(e),
            ) from e
            
        if isinstance(release_data, dp.extras.polars.OnceFrame):
            release_data = release_data.collect().write_json()

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

def extract_group_by_columns(plan: str) -> list | None:
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
    match = re.search(aggregate_by_pattern, plan)

    if match:
        # Extract the columns part
        columns_part = match.group(1)
        # Find all column names inside col("...")
        column_names = re.findall(r'col\("([^"]+)"\)', columns_part)
        return column_names
    return None

def reconstruct_measurement_pipeline(
    query_json: OpenDPModel, metadata: dict
) -> dp.Measurement:
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
        # TODO Might pickle, huge security implications!!
        plan = pl.LazyFrame.deserialize(
            io.StringIO(query_json.opendp_json), format="json"
        )

        groups = extract_group_by_columns(plan.explain())
        output_measure = {
            "laplace": dp.measures.max_divergence(
                T="float",
            ),
            "gaussian": dp.measures.zero_concentrated_divergence(T="float"),
        }[query_json.mechanism]

        lf_domain = get_lf_domain(metadata, groups)

        LOG.info(
            "NOTE: IF THERE IS AN ERROR HERE."
            "Make private lazyframe relies on OPENDP_LIB_PATH variable."
            "This will change shortly to OPENDP_POLARS_LIB_PATH when "
            "https://github.com/opendp/opendp/pull/1839f gets merged."
        )
        opendp_pipe = dp.measurements.make_private_lazyframe(
            lf_domain, dp.metrics.symmetric_distance(), output_measure, plan
        )
    else:
        raise InvalidQueryException(
            f"Unsupported OpenDP pipeline type: {query_json.pipeline_type}"
        )

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

    if output_measure == dp.measures.fixed_smoothed_max_divergence(T=output_type):
        measurement = OpenDPMeasurement.FIXED_SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.max_divergence(T=output_type):
        measurement = OpenDPMeasurement.MAX_DIVERGENCE
    elif output_measure == dp.measures.smoothed_max_divergence(T=output_type):
        measurement = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.zero_concentrated_divergence(T=output_type):
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
