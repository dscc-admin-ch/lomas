from typing import List
from fastapi import HTTPException
from snsql import Privacy, from_connection
import traceback
import pandas as pd

from dp_queries.dp_logic import DPQuerier
import globals
from private_dataset.private_dataset import PrivateDataset

from utils.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
)
from utils.loggr import LOG


class SmartnoiseSQLQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: dict) -> List[float]:
        privacy = Privacy(epsilon=query_json.epsilon, delta=query_json.delta)
        reader = from_connection(
            self.private_dataset.get_pandas_df(), privacy=privacy, metadata=self.private_dataset.get_metadata()
        )

        query_str = query_json.query_str
        try:
            result = reader.get_privacy_cost(query_str)
        except Exception as err:
            print(traceback.format_exc())
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )

        return result

    def query(self, query_json: dict) -> str:
        epsilon, delta = query_json.epsilon, query_json.delta
        privacy = Privacy(epsilon=epsilon, delta=delta)
        reader = from_connection(
            self.private_dataset.get_pandas_df(), privacy=privacy, metadata=self.private_dataset.get_metadata()
        )

        query_str = query_json.query_str
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
                f"SQL Reader generated empty results,"
                f"Epsilon: {epsilon} and Delta: {delta} are too small"
                "to generate output.",
            )

        df_res = pd.DataFrame(result, columns=cols)

        if df_res.isnull().values.any():
            raise HTTPException(
                400,
                f"SQL Reader generated NAN results."
                f" Epsilon: {epsilon} and Delta: {delta} are too small"
                " to generate output.",
            )

        return df_res.to_dict(orient="tight")
