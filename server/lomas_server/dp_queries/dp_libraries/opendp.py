import io
import os
import re
from typing import List, Union

import opendp as dp
import polars as pl
from opendp.metrics import metric_distance_type, metric_type
from opendp.mod import enable_features
from opendp_logger import make_load_json

from constants import DPLibraries, OpenDPDatasetInputMetric, OpenDPMeasurement
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.config import OpenDPConfig
from utils.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from utils.input_models import OpenDPInp
from utils.loggr import LOG


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

    lf_domain = dp.domains.lazyframe_domain(series_domains)

    # Margins
    # TODO Check lengths vs. keys for public info -> not in doc anymore.

    # Global params
    params = {}
    params["max_num_partitions"] = metadata["max_ids"]
    if "rows" in metadata:
        params["max_partition_length"] = metadata["rows"]
    if len(params) > 0:
        lf_domain = dp.domains.with_margin(
            lf_domain,
            by=[],
            public_info="lengths",
            **params,
        )

    # Grouping logic (margin adaptation)
    if by_config:
        params = _update_params_by_grouping(metadata, by_config, params)
        lf_domain = dp.domains.with_margin(
            lf_domain,
            by=by_config,
            public_info="lengths",
            **params,
        )

    return lf_domain


def _update_params_by_grouping(metadata, by_config, params):
    """
    Updates the parameters for margin adaptation based on
    grouping configuration.

    Args:
        metadata (dict): The metadata dictionary.
        by_config (list): Configuration for grouping.
        params (dict): Current parameters dictionary to update.

    Returns:
        dict: Updated parameters dictionary.
    """
    if len(by_config) == 1:
        series_info = metadata["columns"].get(by_config[0])
        _single_group_update_params(metadata, series_info, params)
    else:
        _multiple_group_update_params(metadata, by_config, params)

    params["max_partition_length"] = int(params["max_partition_length"])
    return params


def _single_group_update_params(metadata, series_info, params):
    """
    Updates parameters for single-column grouping configuration.

    Args:
        metadata (dict): The metadata dictionary.
        series_info (dict): Metadata for the series (column).
        params (dict): Current parameters dictionary to update.
    """
    params["max_partition_length"] = int(
        metadata["rows"] * series_info.get("max_partition_length", 1)
    )
    params["max_num_partitions"] = series_info.get("cardinality")

    if "max_influenced_partitions" in series_info:
        params["max_influenced_partitions"] = min(
            metadata["max_ids"],
            series_info.get("max_influenced_partitions"),
        )

    if "max_partition_contributions" in series_info:
        params["max_partition_contributions"] = min(
            metadata["max_ids"],
            series_info.get("max_partition_contributions"),
        )


def _multiple_group_update_params(metadata, by_config, params):
    """
    Updates parameters for multiple-column grouping configuration.

    Args:
        metadata (dict): The metadata dictionary.
        by_config (list): List of columns used for grouping.
        params (dict): Current parameters dictionary to update.
    """
    params["max_num_partitions"] = 1
    params["max_partition_length"] = metadata["rows"]

    for column in by_config:
        series_info = metadata["columns"].get(column)

        if "cardinality" in series_info:
            params["max_num_partitions"] *= series_info["cardinality"]
            params["max_partition_length"] *= series_info[
                "max_partition_length"
            ]

        if "max_influenced_partitions" in series_info:
            params["max_influenced_partitions"] = (
                params.get("max_influenced_partitions", 1)
                * series_info["max_influenced_partitions"]
            )

        if "max_partition_contributions" in series_info:
            params["max_partition_contributions"] = (
                params.get("max_partition_contributions", 1)
                * series_info["max_partition_contributions"]
            )

    if "max_influenced_partitions" in params:
        params["max_influenced_partitions"] = min(
            metadata["max_ids"], params["max_influenced_partitions"]
        )
    if "max_partition_contributions" in params:
        params["max_partition_contributions"] = min(
            metadata["max_ids"],
            params.get("max_partition_contributions"),
        )


class OpenDPQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the OpenDP library.
    """

    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        """Initializer.

        Args:
            private_dataset (PrivateDataset): Private dataset to query.
        """
        super().__init__(private_dataset)

        # Get metadata once and for all
        self.metadata = dict(self.private_dataset.get_metadata())

    def cost(self, query_json: OpenDPInp) -> tuple[float, float]:
        """
        Estimate cost of query

        Args:
            query_json (BaseModel): The JSON request object for the query.

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
            LOG.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP, "Error obtaining cost:" + str(e)
            ) from e

        # Cost interpretation
        match measurement_type:
            case (
                OpenDPMeasurement.FIXED_SMOOTHED_MAX_DIVERGENCE
            ):  # Approximate DP with fix delta
                epsilon, delta = cost
            case OpenDPMeasurement.MAX_DIVERGENCE:  # Pure DP
                epsilon, delta = cost, 0
            case OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE:  # Approximate DP
                if query_json.delta is None:
                    raise InvalidQueryException(
                        "delta must be set for smooth max divergence"
                        + " and zero concentrated divergence."
                    )
                epsilon = cost.epsilon(delta=query_json.delta)
                delta = query_json.delta
            case _:
                raise InternalServerException(
                    f"Invalid measurement type: {measurement_type}"
                )

        return epsilon, delta

    def query(self, query_json: OpenDPInp) -> Union[List, int, float]:
        """Perform the query and return the response.

        Args:
            query_json (BaseModel): The JSON request object for the query.

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
            input_data = self.private_dataset.get_pandas_df().to_csv(
                header=False, index=False
            )
        elif query_json.pipeline_type == "polars":
            input_data = self.private_dataset.get_polars_lf()
        else:  # TODO validate input in json model instead of with if-else statements
            raise InvalidQueryException("invalid pipeline type")

        try:
            release_data = opendp_pipe(input_data)
        except Exception as e:
            LOG.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP,
                "Error executing query:" + str(e),
            ) from e

        if isinstance(release_data, dp.polars.OnceFrame):
            release_data = release_data.collect().write_json()

        return release_data


def is_measurement(pipeline: dp.Measurement) -> None:
    """Check if the pipeline is a measurement.

    Args:
        pipeline (dp.Measurement): The measurement to check.

    Raises:
        InvalidQueryException: If the pipeline is not a measurement.
    """
    if not isinstance(pipeline, dp.Measurement):
        e = (
            "The pipeline provided is not a measurement. "
            + "It cannot be processed in this server."
        )
        LOG.exception(e)
        raise InvalidQueryException(e)


def has_dataset_input_metric(pipeline: dp.Measurement) -> None:
    """Check that the input metric of the pipeline is a dataset metric

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
        LOG.exception(e)
        raise InvalidQueryException(e)

    dataset_input_metric = [m.value for m in OpenDPDatasetInputMetric]
    if not metric_type(pipeline.input_metric) in dataset_input_metric:
        e = (
            f"The input distance metric {pipeline.input_metric} is not a dataset"
            + " input metric. It cannot be processed in this server."
        )
        LOG.exception(e)
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
    query_json: OpenDPInp, metadata: dict
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
        if output_type.origin in ["SMDCurve", "Tuple"]:
            output_type = output_type.args[0]
        else:
            raise InternalServerException(
                f"Cannot process output measure: {output_measure}"
                + f"with output type {output_type}."
            )

    if output_measure == dp.measures.fixed_smoothed_max_divergence(
        T=output_type
    ):
        measurement = OpenDPMeasurement.FIXED_SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.max_divergence(T=output_type):
        measurement = OpenDPMeasurement.MAX_DIVERGENCE
    elif output_measure == dp.measures.smoothed_max_divergence(T=output_type):
        measurement = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.zero_concentrated_divergence(
        T=output_type
    ):
        measurement = OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE
    else:
        raise InternalServerException(
            f"Unknown type of output measure divergence: {output_measure}"
        )
    return measurement


def set_opendp_features_config(opendp_config: OpenDPConfig):
    """Enable opendp features based on config
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
    from opendp._lib import lib_path

    os.environ["OPENDP_LIB_PATH"] = str(lib_path)
