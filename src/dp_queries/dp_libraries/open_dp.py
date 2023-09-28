from fastapi import HTTPException

import opendp_polars as dp
from opendp_polars.mod import enable_features
from opendp_logger import make_load_json
from typing import List
from private_database.private_database import PrivateDatabase
from dp_queries.dp_logic import DPQuerier
from utils.constants import DUMMY_NB_ROWS, DUMMY_SEED
from utils.loggr import LOG

enable_features("contrib")

PT_TYPE = "^py_type:*"


class OpenDPQuerier(DPQuerier):
    def __init__(
        self,
        metadata,
        private_db: PrivateDatabase = None,
        dummy: bool = False,
        dummy_nb_rows: int = DUMMY_NB_ROWS,
        dummy_seed: int = DUMMY_SEED,
        input_data_type: str = "df"
    ) -> None:
        super().__init__(
            metadata, private_db, dummy, dummy_nb_rows, dummy_seed
        )
        self.input_data_type = input_data_type
        self.path = "income_synthetic_data.csv" # TODO: improve

    def cost(self, query_json: dict) -> List[float]:
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        try:
            # TODO: change d_in=1 or 1.0 with the maxrowchanged from metadata
            cost = opendp_pipe.map(d_in=1.0)

        except Exception:
            try:
                cost = opendp_pipe.map(d_in=1)
            except Exception as e:
                LOG.exception(e)
                raise HTTPException(
                    400,
                    "Error obtaining privacy map for the chain. \
                        Please ensure methods return epsilon, \
                            and delta in privacy map. Error:"
                    + str(e),
                )

        epsilon, delta = cost_to_param(cost)
        return epsilon, delta

    def query(self, query_json: dict) -> str:
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        if query_json.input_data_type == "df":
            input_data = self.df.to_csv()
        elif query_json.input_data_type == "path":
            input_data = self.path
        else:
            e = f"Input data type {query_json.input_data_type} not valid for opendp query"
            LOG.exception(e)
            raise HTTPException(400, e)

        try:
            release_data = opendp_pipe(input_data)
        except HTTPException as he:
            LOG.exception(he)
            raise he
        except Exception as e:
            LOG.exception(e)
            raise HTTPException(
                400,
                "Failed when applying chain to data with error: " + str(e),
            )

        return release_data


def is_measurement(value):
    return isinstance(value, dp.Measurement)


def reconstruct_measurement_pipeline(pipeline):
    opendp_pipe = make_load_json(pipeline)

    if not is_measurement(opendp_pipe):
        e = "The pipeline provided is not a measurement. \
                It cannot be processed in this server."
        LOG.exception(e)
        raise HTTPException(400, e)

    return opendp_pipe


def cost_to_param(cost):
    """
    TODO: improve by checking the type (gaussian/laplace) of the output
    like below:
    def is_approx_dp(meas):
    return meas.output_measure == dp.fixed_smoothed_max_divergence(T = float)
    """
    if isinstance(cost, int) or isinstance(cost, float):
        epsilon, delta = cost, 0
    elif isinstance(cost, tuple):
        epsilon, delta = cost[0], cost[1]
    else:
        e = f"Unexpected result from opendp map function: {cost}"
        LOG.exception(e)
        raise HTTPException(
            400,
            "Failed when unpacking opendp cost: " + str(e),
        )
    return epsilon, delta
