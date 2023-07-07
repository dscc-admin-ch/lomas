from typing import List
from fastapi import HTTPException
from snsql import Privacy, from_connection
import traceback
import pandas as pd

from dp_queries.dp_logic import DPQuerier
import globals
from utils.dummy_dataset import make_dummy_dataset
from utils.constants import (
    IRIS_DATASET,
    IRIS_DATASET_PATH,
    IRIS_METADATA_PATH,
    PENGUIN_DATASET,
    PENGUIN_DATASET_PATH,
    PENGUIN_METADATA_PATH,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
)
from utils.loggr import LOG


def smartnoise_dataset_factory(dataset_name: str):
    if dataset_name == IRIS_DATASET:
        if globals.IRIS_QUERIER is None:
            globals.IRIS_QUERIER = SmartnoiseSQLQuerier(
                IRIS_METADATA_PATH,
                IRIS_DATASET_PATH,
            )
        querier = globals.IRIS_QUERIER
    elif dataset_name == PENGUIN_DATASET:
        if globals.PENGUIN_QUERIER is None:
            globals.PENGUIN_QUERIER = SmartnoiseSQLQuerier(
                PENGUIN_METADATA_PATH,
                PENGUIN_DATASET_PATH,
            )
        querier = globals.PENGUIN_QUERIER
    else:
        raise (f"Dataset {dataset_name} unknown.")

    return querier


class SmartnoiseSQLQuerier(DPQuerier):
    def __init__(
        self,
        metadata: dict,
        csv_path: str = None,
        dummy: bool = False,
        dummy_nb_rows: int = DUMMY_NB_ROWS,
        dummy_seed: int = DUMMY_SEED,
    ) -> None:
        self.metadata = metadata

        if dummy:
            self.df = make_dummy_dataset(
                self.metadata, dummy_nb_rows, dummy_seed
            )
        else:
            self.df = pd.read_csv(csv_path)

    def cost(self, query_str: str, eps: float, delta: float) -> List[float]:
        privacy = Privacy(epsilon=eps, delta=delta)
        reader = from_connection(
            self.df, privacy=privacy, metadata=self.metadata
        )

        try:
            result = reader.get_privacy_cost(query_str)
        except Exception as err:
            print(traceback.format_exc())
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )

        return result

    def query(self, query_str: str, eps: float, delta: float) -> str:
        privacy = Privacy(epsilon=eps, delta=delta)
        reader = from_connection(
            self.df, privacy=privacy, metadata=self.metadata
        )

        try:
            result = reader.execute(query_str)
        except Exception as err:
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )
        if globals.CONFIG.develop_mode:
            LOG.warning("********RESULT AFTER QUERY********")
            LOG.warning(result)

        cols = result.pop(0)

        if result == []:
            raise HTTPException(
                400,
                f"SQL Reader generated empty results, \
                    Epsilon: {eps} and Delta: {delta} are too small \
                        to generate output.",
            )

        df_res = pd.DataFrame(result, columns=cols)

        return df_res
