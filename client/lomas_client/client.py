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


# Server constants: warning: MUST match those of server
class DPLibraries(StrEnum):
    SMARTNOISE_SQL = "smartnoise_sql"
    OPENDP = "opendp"


def error_message(res: requests.Response) -> str:
    """_summary_

    Args:
        res (requests.Response): _description_

    Returns:
        str: _description_
    """
    return f"Server error status {res.status_code}: {res.text}"


class Client:
    def __init__(self, url: str, user_name: str, dataset_name: str) -> None:
        """_summary_

        Args:
            url (str): _description_
            user_name (str): _description_
            dataset_name (str): _description_
        """
        self.url = url
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.headers["user-name"] = user_name
        self.dataset_name = dataset_name

    def get_dataset_metadata(
        self,
    ) -> Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
        """_summary_

        Returns:
            Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
                _description_
        """
        res = self._exec("get_dataset_metadata", {"dataset_name": self.dataset_name})
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
        """_summary_

        Args:
            nb_rows (int, optional): _description_. Defaults to DUMMY_NB_ROWS.
            seed (int, optional): _description_. Defaults to DUMMY_SEED.

        Returns:
            Optional[pd.DataFrame]: _description_
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
        """_summary_

        Args:
            query (str): _description_
            epsilon (float): _description_
            delta (float): _description_
            mechanisms (dict[str, str], optional):
                _description_. Defaults to {}.
            postprocess (bool, optional): _description_. Defaults to True.
            dummy (bool, optional): _description_. Defaults to False.
            nb_rows (int, optional): _description_. Defaults to DUMMY_NB_ROWS.
            seed (int, optional): _description_. Defaults to DUMMY_SEED.

        Returns:
            Optional[dict]: _description_
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
        """_summary_

        Args:
            query (str): _description_
            epsilon (float): _description_
            delta (float): _description_
            mechanisms (dict[str, str], optional):
                _description_. Defaults to {}.

        Returns:
            Optional[dict[str, float]]: _description_
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
        """_summary_

        Args:
            opendp_pipeline (dp.Measurement): _description_
            fixed_delta (Optional[float], optional): _description_.
                Defaults to None.
            dummy (bool, optional): _description_. Defaults to False.
            nb_rows (int, optional): _description_. Defaults to DUMMY_NB_ROWS.
            seed (int, optional): _description_. Defaults to DUMMY_SEED.

        Raises:
            Exception: _description_

        Returns:
            Optional[dict]: _description_
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
            if isinstance(response_dict["query_response"], str):
                raise Exception("Not implemented: server should not return dataframes")
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
        """_summary_

        Args:
            opendp_pipeline (dp.Measurement):
                _description_
            fixed_delta (Optional[float], optional):
                _description_. Defaults to None.

        Returns:
            Optional[dict[str, float]]: _description_
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
        """_summary_

        Returns:
            Optional[dict[str, float]]: _description_
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
        """_summary_

        Returns:
            Optional[dict[str, float]]: _description_
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
        """_summary_

        Returns:
            Optional[dict[str, float]]: _description_
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
        """_summary_

        Raises:
            ValueError: _description_

        Returns:
            Optional[List[dict]]: _description_
        """
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_previous_queries", body_json)

        if res.status_code == 200:
            queries = json.loads(res.content.decode("utf8"))["previous_queries"]

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
        """_summary_

        Args:
            endpoint (str): _description_
            body_json (dict, optional): _description_. Defaults to {}.

        Returns:
            requests.Response: _description_
        """
        r = requests.post(
            self.url + "/" + endpoint,
            json=body_json,
            headers=self.headers,
            timeout=50,
        )
        return r
