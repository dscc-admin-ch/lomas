import opendp as dp
from constants import DPLibraries, OpenDPInputType, OpenDPMeasurement
from dp_queries.dp_querier import DPQuerier
from opendp.mod import enable_features
from opendp_logger import make_load_json

# Note: leaving this here, support for opendp_polars
# import polars
from private_dataset.private_dataset import PrivateDataset
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
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: OpenDPInp) -> tuple[float, float]:
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        measurement_type = get_output_measure(opendp_pipe)
        # https://docs.opendp.org/en/stable/user/combinators.html#measure-casting
        if measurement_type == OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE:
            opendp_pipe = dp.combinators.make_zCDP_to_approxDP(opendp_pipe)
            measurement_type = OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE

        max_ids = self.private_dataset.get_metadata()[""]["Schema"]["Table"][
            "max_ids"
        ]
        try:
            cost = opendp_pipe.map(d_in=int(max_ids))
        except Exception:
            try:
                cost = opendp_pipe.map(d_in=float(max_ids))
            except Exception as e:
                LOG.exception(e)
                raise ExternalLibraryException(
                    DPLibraries.OPENDP,
                    "Error obtaining cost:" + str(e),
                )

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

    def query(self, query_json: OpenDPInp) -> str:
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        match query_json.input_data_type:
            case OpenDPInputType.DF:
                input_data = self.private_dataset.get_pandas_df().to_csv(
                    header=False, index=False
                )
            case OpenDPInputType.PATH:
                input_data = self.private_dataset.get_local_path()
            case _:
                raise InvalidQueryException(
                    f"Invalid input data type {query_json.input_data_type}"
                )

        try:
            release_data = opendp_pipe(input_data)
        except Exception as e:
            LOG.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP,
                "Error executing query:" + str(e),
            )

        # Note: leaving this here, support for opendp_polars
        # if isinstance(release_data, polars.dataframe.frame.DataFrame):
        #     release_data = release_data.write_json(file=None)

        return release_data


def is_measurement(value: dp.Measurement) -> bool:
    return isinstance(value, dp.Measurement)


def reconstruct_measurement_pipeline(pipeline: str) -> dp.Measurement:
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
    output_type = opendp_pipe.output_distance_type
    output_measure = opendp_pipe.output_measure

    if output_measure == dp.measures.fixed_smoothed_max_divergence(
        T=output_type
    ):
        return OpenDPMeasurement.FIXED_SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.max_divergence(T=output_type):
        return OpenDPMeasurement.MAX_DIVERGENCE
    elif output_measure == dp.measures.smoothed_max_divergence(T=output_type):
        return OpenDPMeasurement.SMOOTHED_MAX_DIVERGENCE
    elif output_measure == dp.measures.zero_concentrated_divergence(
        T=output_type
    ):
        return OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE
    else:
        raise InternalServerException(
            f"Unknown type of output measure divergence: {output_measure}"
        )
