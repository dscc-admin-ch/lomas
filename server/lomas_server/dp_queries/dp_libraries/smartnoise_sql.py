import pandas as pd
from snsql import Mechanism, Privacy, Stat, from_connection

from constants import MAX_NAN_ITERATION, STATS, DPLibraries
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.error_handler import ExternalLibraryException, InvalidQueryException
from utils.input_models import SNSQLInp, SNSQLInpCost


class SmartnoiseSQLQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the SmartNoiseSQL library.
    """

    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        """Initializer.

        Args:
            private_dataset (PrivateDataset): Private dataset to query.
        """
        super().__init__(private_dataset)

        # Reformat metadata
        metadata = dict(self.private_dataset.get_metadata())
        metadata.update(metadata["columns"])
        del metadata["columns"]
        self.snsql_metadata = {"": {"": {"df": metadata}}}

    def cost(self, query_json: SNSQLInpCost) -> tuple[float, float]:
        """Estimate cost of query

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
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
        """Perform the query and return the response.

        Args:
            query_json (BaseModel): The JSON request object for the query.
            nb_iter (int, optional): Number of trials if output is Nan.
                Defaults to 0.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InvalidQueryException: If the budget values are too small to
                perform the query.

        Returns:
            dict: The dictionary encoding of the resulting pd.DataFrame.
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
    """Set privacy mechanisms on the Privacy object.

    For more information see:
    https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms

    Args:
        privacy (Privacy): Privacy object.
        mechanisms (dict[str, str]): Mechanisms to set.

    Returns:
        Privacy: The updated Privacy object.
    """
    for stat in STATS:
        if stat in mechanisms.keys():
            privacy.mechanisms.map[Stat[stat]] = Mechanism[mechanisms[stat]]
    return privacy
