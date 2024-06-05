import json
from enum import StrEnum
from io import StringIO
from typing import Dict, List, Optional, Union

import opendp as dp
import pandas as pd
import requests
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json


# Opendp_logger
enable_logging()
enable_features("contrib")

# Client constants: may be modified
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42


class DPLibraries(StrEnum):
    """Enum of the DP librairies used in the server
    WARNING: MUST match those of lomas_server
    """

    SMARTNOISE_SQL = "smartnoise_sql"
    OPENDP = "opendp"


def error_message(res: requests.Response) -> str:
    """Generates an error message based on the HTTP response.

    Args:
        res (requests.Response): The response object from an HTTP request.

    Returns:
        str: A formatted string describing the server error,
            including the status code and response text.
    """
    return f"Server error status {res.status_code}: {res.text}"


class Client:
    """Client class to send requests to the server
    Handle all serialisation and deserialisation steps
    """

    def __init__(self, url: str, user_name: str, dataset_name: str) -> None:
        """Initializes the Client with the specified URL, user name, and dataset name.

        Args:
            url (str): The base URL for the API server.
            user_name (str): The name of the user allowed to perform queries.
            dataset_name (str): The name of the dataset to be accessed or manipulated.
        """
        self.url = url
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.headers["user-name"] = user_name
        self.dataset_name = dataset_name

    def get_dataset_metadata(
        self,
    ) -> Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
        """This function retrieves metadata for the dataset.

        Returns:
            Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
                A dictionary containing dataset metadata.
        """
        res = self._exec(
            "get_dataset_metadata", {"dataset_name": self.dataset_name}
        )
        if res.status_code == 200:
            data = res.content.decode("utf8")
            metadata = json.loads(data)
            return metadata

        print(error_message(res))
        return None

    def get_dummy_dataset(
        self,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[pd.DataFrame]:
        """This function retrieves a dummy dataset with optional parameters.

        Args:
            nb_rows (int, optional): The number of rows in the dummy dataset.

                Defaults to DUMMY_NB_ROWS.

            seed (int, optional): The random seed for generating the dummy dataset.

                Defaults to DUMMY_SEED.

        Returns:
            Optional[pd.DataFrame]: A Pandas DataFrame representing the dummy dataset.
        """
        res = self._exec(
            "get_dummy_dataset",
            {
                "dataset_name": self.dataset_name,
                "dummy_nb_rows": nb_rows,
                "dummy_seed": seed,
            },
        )

        if res.status_code == 200:
            data = res.content.decode("utf8")
            df = pd.read_csv(StringIO(data))
            return df
        print(error_message(res))
        return None

    def smartnoise_query(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
        postprocess: bool = True,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
        """This function executes a SmartNoise query.

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
        body_json = {
            "query_str": query,
            "dataset_name": self.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
            "postprocess": postprocess,
        }
        if dummy:
            endpoint = "dummy_smartnoise_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "smartnoise_query"

        res = self._exec(endpoint, body_json)

        if res.status_code == 200:
            data = res.content.decode("utf8")
            response_dict = json.loads(data)
            response_dict["query_response"] = pd.DataFrame.from_dict(
                response_dict["query_response"], orient="tight"
            )
            return response_dict

        print(error_message(res))
        return None

    def estimate_smartnoise_cost(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
    ) -> Optional[dict[str, float]]:
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
        body_json = {
            "query_str": query,
            "dataset_name": self.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
        }
        res = self._exec("estimate_smartnoise_cost", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        print(error_message(res))
        return None

    def opendp_query(
        self,
        opendp_pipeline: dp.Measurement,
        fixed_delta: Optional[float] = None,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.
            fixed_delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).
                In that case a fixed_delta must be provided by the user.
                Defaults to None.
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
            Defaults to DUMMY_SEED.

        Raises:
            Exception: If the server returns dataframes

        Returns:
            Optional[dict]: A Pandas DataFrame containing the query results.
        """
        opendp_json = opendp_pipeline.to_json()
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "fixed_delta": fixed_delta,
        }
        if dummy:
            endpoint = "dummy_opendp_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "opendp_query"

        res = self._exec(endpoint, body_json)
        if res.status_code == 200:
            data = res.content.decode("utf8")
            response_dict = json.loads(data)

            # Opendp outputs can be single numbers or dataframes,
            # we handle the latter here.
            # This is a hack for now, maybe use parquet to send results over.
            # if isinstance(response_dict["query_response"], str):
            #     raise Exception("Not implemented: should not return dataframes")
            # Note: leaving this here. Support for opendp_polars
            # response_dict["query_response"] = polars.read_json(
            #    StringIO(response_dict["query_response"])
            # )

            return response_dict

        print(error_message(res))
        return None

    def estimate_opendp_cost(
        self,
        opendp_pipeline: dp.Measurement,
        fixed_delta: Optional[float] = None,
    ) -> Optional[dict[str, float]]:
        """This function estimates the cost of executing an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.
            fixed_delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.\
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).\
                In that case a fixed_delta must be provided by the user.\
                Defaults to None.


        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        opendp_json = opendp_pipeline.to_json()
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "fixed_delta": fixed_delta,
        }
        res = self._exec("estimate_opendp_cost", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))

        print(error_message(res))
        return None

    def get_initial_budget(self) -> Optional[dict[str, float]]:
        """This function retrieves the initial budget.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the initial budget.
        """
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_initial_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))

        print(error_message(res))
        return None

    def get_total_spent_budget(self) -> Optional[dict[str, float]]:
        """This function retrieves the total spent budget.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the total spent budget.
        """
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_total_spent_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))

        print(error_message(res))
        return None

    def get_remaining_budget(self) -> Optional[dict[str, float]]:
        """This function retrieves the remaining budget.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the remaining budget.
        """
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_remaining_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))

        print(error_message(res))
        return None

    def get_previous_queries(self) -> Optional[List[dict]]:
        """This function retrieves the previous queries of the user.

        Raises:
            ValueError: If an unknown query type is encountered during deserialization.

        Returns:
            Optional[List[dict]]: A list of dictionary containing the different queries
            on the private dataset.
        """
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_previous_queries", body_json)

        if res.status_code == 200:
            queries = json.loads(res.content.decode("utf8"))[
                "previous_queries"
            ]

            if not queries:
                return queries

            deserialised_queries = []
            for query in queries:
                match query["dp_librairy"]:
                    case DPLibraries.SMARTNOISE_SQL:
                        pass
                    case DPLibraries.OPENDP:
                        opdp_query = make_load_json(
                            query["client_input"]["opendp_json"]
                        )
                        query["client_input"]["opendp_json"] = opdp_query
                    case _:
                        raise ValueError(
                            "Cannot deserialise unknown query type:"
                            + f"{query['dp_librairy']}"
                        )

                deserialised_queries.append(query)

            return deserialised_queries

        print(error_message(res))
        return None

    def _exec(self, endpoint: str, body_json: dict = {}) -> requests.Response:
        """Executes a POST request to the specified endpoint with the provided
        JSON body.

        Args:
            endpoint (str): The API endpoint to which the request will be sent.
            body_json (dict, optional): The JSON body to include in the POST request.\
            Defaults to {}.

        Returns:
            requests.Response: The response object resulting from the POST request.
        """
        r = requests.post(
            self.url + "/" + endpoint,
            json=body_json,
            headers=self.headers,
            timeout=50,
        )
        return r
