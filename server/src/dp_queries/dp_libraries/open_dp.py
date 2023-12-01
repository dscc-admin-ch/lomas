from fastapi import HTTPException

import opendp_polars as dp
from opendp_polars.mod import enable_features
from opendp_logger import make_load_json
from typing import List
import polars
from private_dataset.private_dataset import PrivateDataset
from dp_queries.dp_querier import DPQuerier
from constants import (
    OPENDP_INPUT_TYPE_DF,
    OPENDP_INPUT_TYPE_PATH,
)
from utils.loggr import LOG

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

        try:
            cost = opendp_pipe.map(
                d_in=float(
                    self.private_dataset.get_metadata()[""]["Schema"]["Table"][
                        "max_ids"
                    ]
                )
            ) 

        except Exception:
            try:
                cost = opendp_pipe.map(
                    d_in=int(
                        self.private_dataset.get_metadata()[""]["Schema"][
                            "Table"
                        ]["max_ids"]
                    )
                )
            except Exception as e:
                LOG.exception(e)
                raise HTTPException(
                    400,
                    "Error obtaining privacy map for the chain. \
                        Please ensure methods return epsilon, \
                            and delta in privacy map. Error:"
                    + str(e),
                )

        epsilon, delta = cost_to_param(opendp_pipe, cost)
        
        return epsilon, delta

    def query(self, query_json: dict) -> str:
        opendp_pipe = reconstruct_measurement_pipeline(query_json.opendp_json)

        if query_json.input_data_type == OPENDP_INPUT_TYPE_DF:
            input_data = self.private_dataset.get_pandas_df().to_csv(
                header=False, index=False
            )
        elif query_json.input_data_type == OPENDP_INPUT_TYPE_PATH:
            input_data = self.private_dataset.get_local_path()
        else:
            e = (
                f"Input data type {query_json.input_data_type}"
                "not valid for opendp query"
            )
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

        if isinstance(release_data, polars.dataframe.frame.DataFrame):
            release_data = release_data.write_json(file=None)

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


def cost_to_param(opendp_pipe, cost):
    # Currently works with laplace noise (tested with example from client notebook)
    #TODO: Test with gaussian noise and check how the cost is returned

    measurement_type = infer_measurement_type(opendp_pipe)
    if measurement_type == "gaussian":
        epsilon, delta = cost, 0  # should be cost[0], cost[1] (?) but for some reason
        # cost is a float in the client notebook example when calling then_gaussian
        # in the client notebook example 
    elif measurement_type == "laplace":
        epsilon, delta = cost, 0
    else:
        e = f"This measurement type is not yet supported: {opendp_pipe.output_measure}"
        LOG.exception(e)
        raise HTTPException(
            400,
            "Failed when unpacking opendp cost: " + str(e),
        )
    
    return epsilon, delta

def infer_measurement_type(opendp_pipe):
    if  (opendp_pipe.output_measure != dp.measures.max_divergence(T=float) and
         opendp_pipe.output_measure != dp.measures.zero_concentrated_divergence(T=float)):
        measurement_type = "unknown" 
    if opendp_pipe.output_measure == dp.measures.max_divergence(T=float):
        measurement_type = "laplace"
    elif opendp_pipe.output_measure == dp.measures.zero_concentrated_divergence(T=float):
        measurement_type = "gaussian"
    
    return measurement_type