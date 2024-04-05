import opendp as dp
from opendp.mod import enable_features
from opendp_logger import make_load_json
from typing import List

# Note: leaving this here, support for opendp_polars
# import polars
from private_dataset.private_dataset import PrivateDataset
from dp_queries.dp_querier import DPQuerier
from constants import DPLibraries, OpenDPInputType
from utils.loggr import LOG
from utils.utils import (
    ExternalLibraryException,
    InvalidQueryException,
)


enable_features("contrib")

PT_TYPE = "^py_type:*"


class OpenDPQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: dict) -> List[float]:
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

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

        if isinstance(cost, int) or isinstance(cost, float):
            epsilon, delta = cost, 0
        elif isinstance(cost, tuple) and len(cost) == 2:
            epsilon, delta = cost[0], cost[1]
        else:
            e = f"Cost cannot be converted to epsilon, delta format: {cost}"
            LOG.exception(e)
            raise Exception(e)

        return epsilon, delta

    def query(self, query_json: dict) -> str:
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


def is_measurement(value):
    return isinstance(value, dp.Measurement)


def reconstruct_measurement_pipeline(pipeline):
    opendp_pipe = make_load_json(pipeline)

    if not is_measurement(opendp_pipe):
        e = (
            "The pipeline provided is not a measurement. "
            + "It cannot be processed in this server."
        )
        LOG.exception(e)
        raise InvalidQueryException(e)

    return opendp_pipe
