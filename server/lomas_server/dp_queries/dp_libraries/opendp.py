from typing import List, Union

import opendp as dp
from opendp.mod import enable_features
from opendp_logger import make_load_json

from constants import DPLibraries, OpenDPMeasurement
from dp_queries.dp_querier import DPQuerier
from utils.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from utils.input_models import OpenDPInp
from utils.loggr import LOG

enable_features("contrib")

PT_TYPE = "^py_type:*"


class OpenDPQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the OpenDP library.
    """

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
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        measurement_type = get_output_measure(opendp_pipe)
        # https://docs.opendp.org/en/stable/user/combinators.html#measure-casting
        if measurement_type == OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE:
            opendp_pipe = dp.combinators.make_zCDP_to_approxDP(opendp_pipe)
            measurement_type = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE

        max_ids = self.private_dataset.get_metadata()["max_ids"]
        try:
            cost = opendp_pipe.map(d_in=int(max_ids))
        except TypeError:
            try:
                cost = opendp_pipe.map(d_in=float(max_ids))
            except Exception as e:
                LOG.exception(e)
                raise ExternalLibraryException(
                    DPLibraries.OPENDP,
                    "Error obtaining cost:" + str(e),
                ) from e
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
                        "fixed_delta must be set for smooth max divergence."
                    )
                epsilon = cost.epsilon(delta=query_json.fixed_delta)
                delta = query_json.fixed_delta
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
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        input_data = self.private_dataset.get_pandas_df().to_csv(
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

        return release_data


def is_measurement(value: dp.Measurement) -> bool:
    """Check if the value is a measurement.

    Args:
        value (dp.Measurement): The measurement to check.

    Returns:
        bool: True if the value is a measurement, False otherwise.
    """
    return isinstance(value, dp.Measurement)


def reconstruct_measurement_pipeline(pipeline: str) -> dp.Measurement:
    """Reconstruct OpenDP pipeline from json representation.

    Args:
        pipeline (str): The JSON string encoding of the pipeline.

    Raises:
        InvalidQueryException: If the pipeline is not a measurement.

    Returns:
        dp.Measurement: The reconstructed pipeline.
    """
    opendp_pipe = make_load_json(pipeline)

    if not is_measurement(opendp_pipe):
        e = (
            "The pipeline provided is not a measurement. "
            + "It cannot be processed in this server."
        )
        LOG.exception(e)
        raise InvalidQueryException(e)

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
