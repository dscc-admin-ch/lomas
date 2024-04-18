from typing import List

import pandas as pd
from constants import MAX_NAN_ITERATION, STATS, DPLibraries
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from snsql import Mechanism, Privacy, Stat, from_connection
from utils.error_handler import ExternalLibraryException, InvalidQueryException
from utils.input_models import SNSQLInp, SNSQLInpCost


class SmartnoiseSQLQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: SNSQLInpCost) -> List[float]:
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
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error obtaining cost:" + str(e),
            )

        return result

    def query(self, query_json: SNSQLInp, nb_iter: int = 0) -> dict:
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
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error executing query:" + str(e),
            )

        if not query_json.postprocess:
            result = list(result)

        cols = result.pop(0)
        if result == []:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
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
                raise InvalidQueryException(
                    f"SQL Reader generated NAN results."
                    f" Epsilon: {epsilon} and Delta: {delta} are too small"
                    " to generate output.",
                )

        return df_res.to_dict(orient="tight")


def set_mechanisms(privacy: Privacy, mechanisms: dict[str, str]) -> Privacy:
    # https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms
    for stat in STATS:
        if stat in mechanisms.keys():
            privacy.mechanisms.map[Stat[stat]] = Mechanism[mechanisms[stat]]
    return privacy
