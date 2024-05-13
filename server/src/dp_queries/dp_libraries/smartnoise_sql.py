from typing import List

import pandas as pd
from snsql import Mechanism, Privacy, Stat, from_connection

from constants import MAX_NAN_ITERATION, STATS, DPLibraries
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.error_handler import ExternalLibraryException, InvalidQueryException
from utils.input_models import SNSQLInp, SNSQLInpCost


class SmartnoiseSQLQuerier(DPQuerier):
    """Class to handle smartnoise-sql queries"""

    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        """_summary_

        Args:
            private_dataset (PrivateDataset): _description_
        """
        super().__init__(private_dataset)

        # Reformat metadata
        metadata = dict(self.private_dataset.get_metadata())
        metadata.update(metadata["columns"])
        del metadata["columns"]
        self.snsql_metadata = {"": {"": {"df": metadata}}}

    def cost(self, query_json: SNSQLInpCost) -> List[float]:
        """_summary_

        Args:
            query_json (SNSQLInpCost): _description_

        Raises:
            ExternalLibraryException: _description_

        Returns:
            List[float]: _description_
        """
        privacy = Privacy(epsilon=query_json.epsilon, delta=query_json.delta)
        privacy = set_mechanisms(privacy, query_json.mechanisms)

        reader = from_connection(
            self.private_dataset.get_pandas_df(),
            privacy=privacy,
            metadata=self.snsql_metadata,
        )

        try:
            result = reader.get_privacy_cost(query_json.query_str)
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error obtaining cost: " + str(e),
            ) from e

        return result

    def query(self, query_json: SNSQLInp, nb_iter: int = 0) -> dict:
        """_summary_

        Args:
            query_json (SNSQLInp): _description_
            nb_iter (int, optional): _description_. Defaults to 0.

        Raises:
            ExternalLibraryException: _description_
            ExternalLibraryException: _description_
            InvalidQueryException: _description_

        Returns:
            dict: _description_
        """
        epsilon, delta = query_json.epsilon, query_json.delta

        privacy = Privacy(epsilon=epsilon, delta=delta)
        privacy = set_mechanisms(privacy, query_json.mechanisms)

        reader = from_connection(
            self.private_dataset.get_pandas_df(),
            privacy=privacy,
            metadata=self.snsql_metadata,
        )

        try:
            result = reader.execute(
                query_json.query_str, postprocess=query_json.postprocess
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error executing query:" + str(e),
            ) from e

        if not query_json.postprocess:
            result = list(result)
            cols = [f"res_{i}" for i in range(len(result))]
        else:
            cols = result.pop(0)
        if result == []:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                f"SQL Reader generated empty results,"
                f"Epsilon: {epsilon} and Delta: {delta} are too small"
                " to generate output.",
            )

        df_res = pd.DataFrame(result, columns=cols)

        if df_res.isnull().values.any():
            # Try again up to MAX_NAN_ITERATION
            if nb_iter < MAX_NAN_ITERATION:
                nb_iter += 1
                return self.query(query_json, nb_iter)

            raise InvalidQueryException(
                f"SQL Reader generated NAN results."
                f" Epsilon: {epsilon} and Delta: {delta} are too small"
                " to generate output.",
            )

        return df_res.to_dict(orient="tight")


def set_mechanisms(privacy: Privacy, mechanisms: dict[str, str]) -> Privacy:
    """_summary_

    Args:
        privacy (Privacy): _description_
        mechanisms (dict[str, str]): _description_

    Returns:
        Privacy: _description_
    """
    # https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms
    for stat in STATS:
        if stat in mechanisms.keys():
            privacy.mechanisms.map[Stat[stat]] = Mechanism[mechanisms[stat]]
    return privacy
