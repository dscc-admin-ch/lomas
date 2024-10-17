from typing import Optional, Type

from lomas_core.models.requests import (
    SmartnoiseSQLDummyQueryModel,
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response


class SmartnoiseSQLClient:
    """A client for executing and estimating the cost of SmartNoise SQL queries."""

    def __init__(self, http_client: LomasHttpClient):
        self.http_client = http_client

    def cost(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
    ) -> Optional[CostResponse]:
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
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        body_dict = {
            "query_str": query,
            "dataset_name": self.http_client.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
        }
        body = SmartnoiseSQLRequestModel.model_validate(body_dict)
        res = self.http_client.post("estimate_smartnoise_sql_cost", body)

        return validate_model_response(res, CostResponse)

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
    ) -> Optional[QueryResponse]:
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
            Optional[dict]: A Pandas DataFrame containing the query results.
        """
        body_dict = {
            "query_str": query,
            "dataset_name": self.http_client.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
            "postprocess": postprocess,
        }

        request_model: Type[SmartnoiseSQLRequestModel]
        if dummy:
            endpoint = "dummy_smartnoise_sql_query"
            body_dict["dummy_nb_rows"] = nb_rows
            body_dict["dummy_seed"] = seed
            request_model = SmartnoiseSQLDummyQueryModel
        else:
            endpoint = "smartnoise_sql_query"
            request_model = SmartnoiseSQLQueryModel

        body = request_model.model_validate(body_dict)
        res = self.http_client.post(endpoint, body)

        return validate_model_response(res, QueryResponse)
