from returns.io import IOResultE
from returns.pipeline import flow
from returns.pointfree import map_

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response
from lomas_core.models.requests import (
    SmartnoiseSQLDummyQueryModel,
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse


class SmartnoiseSQLClient:
    """A client for executing and estimating the cost of SmartNoise SQL queries."""

    def __init__(self, http_client: LomasHttpClient) -> None:
        self.http_client = http_client

    def cost(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
    ) -> IOResultE[CostResponse]:
        """This function estimates the cost of executing a SmartNoise query.

        Args:
            query (str): The SQL query to estimate the cost for. NOTE: the table name \
                is df, the query must end with “FROM df”.
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
                mechanisms (dict[str, str], optional): Dictionary of mechanisms for the\
                query `See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__
                Defaults to {}.

        Returns:
            CostResponse: The estimated cost.
        """
        return flow(
            {
                "query_str": query,
                "dataset_name": self.http_client.config.dataset_name,
                "epsilon": epsilon,
                "delta": delta,
                "mechanisms": mechanisms,
            },
            SmartnoiseSQLRequestModel.model_validate,
            lambda body: self.http_client.post("estimate_smartnoise_sql_cost", body),
            map_(validate_model_response(self.http_client, CostResponse)),
        )

    def query(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
        postprocess: bool = True,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> IOResultE[QueryResponse]:
        """This function executes a SmartNoise SQL query.

        Args:
            query (str): The SQL query to execute.
                NOTE: the table name is df, the query must end with “FROM df”.
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
            mechanisms (dict[str, str], optional): Dictionary of mechanisms for the\
                query `See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms>`__

                Defaults to {}.
            postprocess (bool, optional): Whether to postprocess the query results.\
                `See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__

                Defaults to True.
            dummy (bool, optional): Whether to use a dummy dataset.

                Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.

                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.

                Defaults to DUMMY_SEED.

        Returns:
            QueryResponse: A Pandas DataFrame containing the query results.
        """
        body_dict = {
            "query_str": query,
            "dataset_name": self.http_client.config.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
            "postprocess": postprocess,
        }
        if dummy:
            return flow(
                {**body_dict, "dummy_nb_rows": nb_rows, "dummy_seed": seed},
                SmartnoiseSQLDummyQueryModel.model_validate,
                lambda body: self.http_client.post("dummy_smartnoise_sql_query", body),
                map_(validate_model_response(self.http_client, QueryResponse)),
            )
        return flow(
            body_dict,
            SmartnoiseSQLQueryModel.model_validate,
            lambda body: self.http_client.post("smartnoise_sql_query", body),
            map_(validate_model_response(self.http_client, QueryResponse)),
        )
