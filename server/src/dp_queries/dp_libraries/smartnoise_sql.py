from typing import List
from fastapi import HTTPException
from snsql import Privacy, from_connection, Stat, Mechanism
import traceback
import pandas as pd

from constants import MAX_NAN_ITERATION, STATS
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.loggr import LOG


class SmartnoiseSQLQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: dict) -> List[float]:
        privacy = Privacy(epsilon=query_json.epsilon, delta=query_json.delta)
        privacy = set_mechanisms(privacy, query_json.mechanisms)

        reader = from_connection(
            self.private_dataset.get_pandas_df(),
            privacy=privacy,
            metadata=self.private_dataset.get_metadata(),
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

    def query(self, query_json: dict, nb_iter=0) -> str:
        epsilon, delta = query_json.epsilon, query_json.delta

        privacy = Privacy(epsilon=epsilon, delta=delta)
        privacy = set_mechanisms(privacy, query_json.mechanisms)

        reader = from_connection(
            self.private_dataset.get_pandas_df(),
            privacy=privacy,
            metadata=self.private_dataset.get_metadata(),
        )

        query_str = query_json.query_str
        try:
            result = reader.execute(
                query_str, postprocess=query_json.postprocess
            )
        except Exception as err:
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )

        if not query_json.postprocess:
            result = list(result)

        # Should only be printed if logging level is debug
        LOG.debug("********RESULT AFTER QUERY********")
        LOG.debug(result)

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
            # Try again up to MAX_NAN_ITERATION
            if nb_iter < MAX_NAN_ITERATION:
                nb_iter += 1
                return self.query(query_json, nb_iter)
            else:
                raise HTTPException(
                    400,
                    f"SQL Reader generated NAN results."
                    f" Epsilon: {epsilon} and Delta: {delta} are too small"
                    " to generate output.",
                )

        return df_res.to_dict(orient="tight")


def set_mechanisms(privacy, mechanisms):
    # https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms
    for stat in STATS:
        if stat in mechanisms.keys():
            privacy.mechanisms.map[Stat[stat]] = Mechanism[mechanisms[stat]]
    return privacy
