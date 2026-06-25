import pandas as pd
from aio_pika.patterns.rpc import Proxy
from csvw_eo.csvw_to_smartnoise_sql import csvw_to_smartnoise_sql
from snsql import Mechanism, Privacy, Stat, from_connection
from snsql.reader.base import Reader
from sqlglot import exp, parse_one

from lomas_core.constants import DPLibraries
from lomas_core.exceptions import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.models.requests import (
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import SmartnoiseSQLQueryResult
from lomas_server.constants import SSQL_MAX_ITERATION, SSQL_STATS
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier


class SmartnoiseSQLQuerier(
    DPQuerier[SmartnoiseSQLRequestModel, SmartnoiseSQLQueryModel, SmartnoiseSQLQueryResult]
):
    """Concrete implementation of the DPQuerier ABC for the SmartNoiseSQL library."""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: Proxy,
    ) -> None:
        super().__init__(data_connector, admin_database)
        self.reader: Reader | None = None
        self.query_columns: list[str] = []

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

        df = self.data_connector.get_pandas_df()

        # Extract query columns, fallback to the first column if none are found
        self.query_columns = get_query_columns(query_json.query_str) or [df.columns[0]]
        missing = [col for col in self.query_columns if col not in df.columns]
        if missing:
            raise InvalidQueryException(f"Query requested columns not found in DataFrame: {missing}")

        # Subset DataFrame to only the relevant columns
        df = df[self.query_columns]

        # Prepare metadata in smartnoise-sql format
        metadata = self.data_connector.metadata
        metadata.columns = [col for col in metadata.columns if col.name in self.query_columns]

        smartnoise_metadata = csvw_to_smartnoise_sql(metadata.to_dict())
        # Only keep self.query_columns
        self.reader = from_connection(
            df,
            privacy=privacy,
            metadata=smartnoise_metadata,
        )
        try:
            epsilon, delta = self.reader.get_privacy_cost(query_json.query_str)

        except Exception as e:
            raise ExternalLibraryException(DPLibraries.SMARTNOISE_SQL, f"Error obtaining cost: {e}") from e

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
            raise InternalServerException("Smartnoise SQL `query` method called before `cost` method")

        try:
            result = self.reader.execute(query_json.query_str, postprocess=query_json.postprocess)
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SQL,
                "Error executing query:" + str(e),
            ) from e
        if not query_json.postprocess:
            result = next(iter(result))
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

        # Check for NaNs in any of the new columns
        new_columns = [col for col in df_res.columns if col not in self.query_columns]
        if df_res[new_columns].isna().any().any():
            if nb_iter < SSQL_MAX_ITERATION:
                nb_iter += 1
                return self.query_with_iter(query_json, nb_iter)

            raise InvalidQueryException(
                f"SQL Reader generated NaN results. "
                f"Epsilon: {epsilon}, Delta: {delta} — too small to generate valid output."
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
        if stat in mechanisms:
            privacy.mechanisms.map[Stat[stat]] = Mechanism[mechanisms[stat]]
    return privacy


def get_query_columns(query: str) -> list[str]:
    """
    Extract all column names used in a SQL query.

    Traverses the query AST (Abstract Syntax Tree) to find every
    column reference across SELECT, WHERE, GROUP BY, ORDER BY, etc.
    Assumes only one table is present in the query.

    Args:
        query (str): SQL query string.

    Returns:
        list[str]: List of unique column names used in the query.
    """
    # Parse SQL into an expression tree
    expression = parse_one(query)

    # Extract all column references from anywhere in the query
    columns = [col.name for col in expression.find_all(exp.Column)]

    return list(set(columns))
