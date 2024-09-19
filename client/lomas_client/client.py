import base64
import json
import pickle
from typing import Dict, List, Optional, Union

import pandas as pd
import requests
from fastapi import status
from lomas_core.constants import DPLibraries
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json

from lomas_client.constants import (
    CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
)
from lomas_client.utils import raise_error

# Opendp_logger
enable_logging()
enable_features("contrib")


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
        res = self._exec("get_dataset_metadata", {"dataset_name": self.dataset_name})
        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            metadata = json.loads(data)
            return metadata

        raise_error(res)
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

        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            response = json.loads(data)
            dummy_df = pd.DataFrame(response["dummy_dict"])
            dummy_df = dummy_df.astype(response["dtypes"])
            for col in response["datetime_columns"]:
                dummy_df[col] = pd.to_datetime(dummy_df[col])
            return dummy_df

        raise_error(res)
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

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        raise_error(res)
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

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        raise_error(res)
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

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        raise_error(res)
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

        if res.status_code == status.HTTP_200_OK:
            queries = json.loads(res.content.decode("utf8"))["previous_queries"]

            if not queries:
                return queries

            deserialised_queries = []
            for query in queries:
                match query["dp_librairy"]:
                    case DPLibraries.SMARTNOISE_SQL:
                        pass
                    case DPLibraries.SMARTNOISE_SYNTH:
                        return_model = query["client_input"]["return_model"]
                        res = query["response"]["query_response"]
                        if return_model:
                            query["response"]["query_response"] = pickle.loads(
                                base64.b64decode(res)
                            )
                        else:
                            query["response"]["query_response"] = pd.DataFrame(res)
                    case DPLibraries.OPENDP:
                        opdp_query = make_load_json(
                            query["client_input"]["opendp_json"]
                        )
                        query["client_input"]["opendp_json"] = opdp_query
                    case DPLibraries.DIFFPRIVLIB:
                        model = base64.b64decode(
                            query["response"]["query_response"]["model"]
                        )
                        query["response"]["query_response"]["model"] = pickle.loads(
                            model
                        )
                    case _:
                        raise ValueError(
                            "Cannot deserialise unknown query type:"
                            + f"{query['dp_librairy']}"
                        )

                deserialised_queries.append(query)

            return deserialised_queries

        raise_error(res)
        return None

    def _exec(
        self,
        endpoint: str,
        body_json: dict = {},
        read_timeout: int = DEFAULT_READ_TIMEOUT,
    ) -> requests.Response:
        """Executes a POST request to the specified endpoint with the provided
        JSON body.

        Args:
            endpoint (str): The API endpoint to which the request will be sent.
            body_json (dict, optional): The JSON body to include in the POST request.\
                Defaults to {}.
            read_timeout (int): number of seconds that client wait for the server
                to send a response.
                Defaults to DEFAULT_READ_TIMEOUT.

        Returns:
            requests.Response: The response object resulting from the POST request.
        """
        r = requests.post(
            self.url + "/" + endpoint,
            json=body_json,
            headers=self.headers,
            timeout=(CONNECT_TIMEOUT, read_timeout),
        )
        return r
