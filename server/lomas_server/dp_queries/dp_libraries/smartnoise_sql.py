from typing import Optional

import pandas as pd
from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.models.collections import Metadata
from lomas_core.models.requests import (
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import SmartnoiseSQLQueryResult
from snsql import Mechanism, Privacy, Stat, from_connection
from snsql.reader.base import Reader

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import SSQL_MAX_ITERATION, SSQL_STATS
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier


class SmartnoiseSQLQuerier(
    DPQuerier[
        SmartnoiseSQLRequestModel, SmartnoiseSQLQueryModel, SmartnoiseSQLQueryResult
    ]
):
    """Concrete implementation of the DPQuerier ABC for the SmartNoiseSQL library."""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: AdminDatabase,
    ) -> None:
        super().__init__(data_connector, admin_database)
        self.reader: Optional[Reader] = None

    def cost(self, query_json: SmartnoiseSQLRequestModel) -> tuple[float, float]:
        """Estimate cost of query.

        Args:
            query_json (SmartnoiseSQLModelCost): JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        privacy = Privacy(epsilon=query_json.epsilon, delta=query_json.delta)
        privacy = set_mechanisms(privacy, query_json.mechanisms)

        metadata = self.data_connector.get_metadata()
        smartnoise_metadata = convert_to_smartnoise_metadata(metadata)

        self.reader = from_connection(
            self.data_connector.get_pandas_df(),
            privacy=privacy,
            metadata=smartnoise_metadata,
        )

        try:
            epsilon, delta = self.reader.get_privacy_cost(query_json.query_str)
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error obtaining cost: " + str(e),
            ) from e

        return epsilon, delta

    def query(self, query_json: SmartnoiseSQLQueryModel) -> SmartnoiseSQLQueryResult:
        """Performs the query and returns the response.

        Args:
            query_json (SmartnoiseSQLQueryModel): The request model object.

        Returns:
            dict: The dictionary encoding of the result pd.DataFrame.
        """
        return self.query_with_iter(query_json)

    def query_with_iter(
        self, query_json: SmartnoiseSQLQueryModel, nb_iter: int = 0
    ) -> SmartnoiseSQLQueryResult:
        """Perform the query and return the response.

        Args:
            query_json (SmartnoiseSQLQueryModel): Request object for the query.
            nb_iter (int, optional): Number of trials if output is Nan.
                Defaults to 0.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InvalidQueryException: If the budget values are too small to
                perform the query.

        Returns:
            SmartnoiseSQLQueryResult:
                The dictionary encoding of the resulting pd.DataFrame.
        """
        epsilon, delta = query_json.epsilon, query_json.delta

        if self.reader is None:
            raise InternalServerException(
                "Smartnoise SQL `query` method called before `cost` method"
            )

        try:
            result = self.reader.execute(
                query_json.query_str, postprocess=query_json.postprocess
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error executing query:" + str(e),
            ) from e
        if not query_json.postprocess:
            result = list(result)[0]
            cols = [f"res_{i}" for i in range(len(result))]
            result = [result]
        else:
            cols = result.pop(0)
        if result == []:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                f"SQL Reader generated empty results. "
                f"Epsilon: {epsilon} and Delta: {delta} are too small"
                " to generate output.",
            )

        df_res = pd.DataFrame(result, columns=cols)

        if df_res.isnull().values.any():
            # Try again up to SSQL_MAX_ITERATION
            if nb_iter < SSQL_MAX_ITERATION:
                nb_iter += 1
                return self.query_with_iter(query_json, nb_iter)

            raise InvalidQueryException(
                f"SQL Reader generated NAN results. "
                f"Epsilon: {epsilon} and Delta: {delta} are too small "
                "to generate output.",
            )
        return SmartnoiseSQLQueryResult(df=df_res)


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
    for stat in SSQL_STATS:
        if stat in mechanisms.keys():
            privacy.mechanisms.map[Stat[stat]] = Mechanism[mechanisms[stat]]
    return privacy


def convert_to_smartnoise_metadata(metadata: Metadata) -> dict:
    """Convert Lomas metadata to smartnoise metadata format (for SQL).

    Args:
        metadata (Metadata): Dataset metadata from admin database
    Returns:
        dict: metadata of the dataset in smartnoise-sql format
    """
    metadata_dict = metadata.model_dump()
    metadata_dict.update(metadata_dict["columns"])
    del metadata_dict["columns"]
    return {"": {"": {"df": metadata_dict}}}
