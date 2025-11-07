import logging
import os

import opendp as dp
import polars as pl
from opendp._lib import lib_path
from opendp.metrics import metric_distance_type, metric_type
from opendp.mod import enable_features

from lomas_core.constants import DPLibraries, OpenDpPipelineType
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.models.constants import MetadataColumnType, OpenDPFeatures
from lomas_core.models.requests import OpenDPQueryModel, OpenDPRequestModel
from lomas_core.models.responses import OpenDPPolarsQueryResult, OpenDPQueryResult
from lomas_core.opendp_utils import reconstruct_measurement_pipeline
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import OpenDPDatasetInputMetric, OpenDPMeasurement
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier

logger = logging.getLogger(__name__)


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
        self.metadata = self.data_connector.metadata.model_dump()

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
        validate_measurement_pipeline(opendp_pipe)

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
            logger.exception(e)
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
        validate_measurement_pipeline(opendp_pipe)

        if query_json.pipeline_type == OpenDpPipelineType.LEGACY:
            input_data = self.data_connector.get_pandas_df().to_csv(header=False, index=False)
        elif query_json.pipeline_type == OpenDpPipelineType.POLARS:
            input_data = self.data_connector.get_polars_lf()
            # OpenDP does not allow None on string columns

            # Build expressions to update the LazyFrame. LazyFrames are immutable
            # and do not support direct item assignment (not supported: input_data[col] = ...)
            expressions = []
            for col, val in self.metadata["columns"].items():
                if val["type"] in {MetadataColumnType.STRING, MetadataColumnType.DATETIME}:
                    expressions.append(pl.col(col).fill_null("").alias(col))

            input_data = input_data.with_columns(expressions)
        else:  # TODO 401 validate input in json model instead of with if-else statements
            raise InternalServerException(
                f"""Invalid pipeline type: '{query_json.pipeline_type}.'
                                        Should be legacy or polars"""
            )
        try:
            release_data = opendp_pipe(input_data)
        except Exception as e:
            logger.exception(e)
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
        logger.error(e)
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
        logger.error(e)
        raise InvalidQueryException(e)

    dataset_input_metric = [m.value for m in OpenDPDatasetInputMetric]
    if metric_type(pipeline.input_metric) not in dataset_input_metric:
        e = (
            f"The input distance metric {pipeline.input_metric} is not a dataset"
            + " input metric. It cannot be processed in this server."
        )
        logger.error(e)
        raise InvalidQueryException(e)


def validate_measurement_pipeline(opendp_pipe: dp.Measurement) -> None:
    """Verify that the pipeline is safe and valid.

    Args:
        pipeline (dp.Measurement): The pipeline to check.

    Raises:
        InvalidQueryException: If the pipeline does not meet the requirements.
    """
    is_measurement(opendp_pipe)
    has_dataset_input_metric(opendp_pipe)


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
        if output_type.origin in {"SMDCurve", "Tuple"}:  # TODO 360 : constant.
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


def set_opendp_features_config(features: OpenDPFeatures) -> None:
    """Enable opendp features based on config.

    See https://github.com/opendp/opendp/discussions/304

    Also sets the "OPENDP_POLARS_LIB_PATH" environment variable
    for correctly creating private lazyframes from deserialized
    polars plans.
    """
    for feat in features:
        logger.debug(f"OpenDP: enabling feature: {feat}")
        enable_features(feat)

    # Set DP Libraries config
    os.environ["OPENDP_LIB_PATH"] = str(lib_path)
