import opendp as dp
from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.logger import LOG
from lomas_core.models.config import OpenDPConfig
from lomas_core.models.requests import (
    OpenDPQueryModel,
    OpenDPRequestModel,
)
from lomas_core.models.responses import OpenDPQueryResult
from opendp.metrics import metric_distance_type, metric_type
from opendp.mod import enable_features
from opendp_logger import make_load_json

from lomas_server.constants import OpenDPDatasetInputMetric, OpenDPMeasurement
from lomas_server.dp_queries.dp_querier import DPQuerier


class OpenDPQuerier(DPQuerier[OpenDPRequestModel, OpenDPQueryModel, OpenDPQueryResult]):
    """Concrete implementation of the DPQuerier ABC for the OpenDP library."""

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
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        measurement_type = get_output_measure(opendp_pipe)
        # https://docs.opendp.org/en/stable/user/combinators.html#measure-casting
        if measurement_type == OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE:
            opendp_pipe = dp.combinators.make_zCDP_to_approxDP(opendp_pipe)
            measurement_type = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE

        max_ids = self.data_connector.get_metadata().max_ids
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
                if query_json.fixed_delta is None:
                    raise InvalidQueryException(
                        "fixed_delta must be set for smooth max divergence"
                        + " and zero concentrated divergence."
                    )
                epsilon = cost.epsilon(delta=query_json.fixed_delta)
                delta = query_json.fixed_delta
            case _:
                raise InternalServerException(
                    f"Invalid measurement type: {measurement_type}"
                )

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
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        input_data = self.data_connector.get_pandas_df().to_csv(
            header=False, index=False
        )

        try:
            release_data = opendp_pipe(input_data)
        except Exception as e:
            LOG.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP,
                "Error executing query:" + str(e),
            ) from e

        return OpenDPQueryResult(value=release_data)


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


def reconstruct_measurement_pipeline(pipeline: str) -> dp.Measurement:
    """Reconstruct OpenDP pipeline from json representation.

    Args:
        pipeline (str): The JSON string encoding of the pipeline.

    Raises:
        InvalidQueryException: If the pipeline is not a measurement.

    Returns:
        dp.Measurement: The reconstructed pipeline.
    """
    # Reconstruct pipeline
    opendp_pipe = make_load_json(pipeline)

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
                f"Cannot process output measure: {output_measure}"
                + f"with output type {output_type}."
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
        raise InternalServerException(
            f"Unknown type of output measure divergence: {output_measure}"
        )
    return measurement


def set_opendp_features_config(opendp_config: OpenDPConfig):
    """Enable opendp features based on config.

    See https://github.com/opendp/opendp/discussions/304

    Args:
        opendp_config (OpenDPConfig): OpenDP configurations
    """
    if opendp_config.contrib:
        enable_features("contrib")

    if opendp_config.floating_point:
        enable_features("floating-point")

    if opendp_config.honest_but_curious:
        enable_features("honest-but-curious")
