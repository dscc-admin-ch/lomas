import json
from enum import StrEnum
from io import StringIO
from typing import Dict, List, Optional, Union

import opendp as dp
import pandas as pd
import requests
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json

# Note: leaving this here. Support for opendp_polars
# import polars

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
    return f"Server error status {res.status_code}: {res.text}"


class Client:
    def __init__(self, url: str, user_name: str, dataset_name: str) -> None:
        self.url = url
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.headers["user-name"] = user_name
        self.dataset_name = dataset_name

    def get_dataset_metadata(
        self,
    ) -> Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
        res = self._exec(
            "get_dataset_metadata", {"dataset_name": self.dataset_name}
        )
        if res.status_code == 200:
            data = res.content.decode("utf8")
            metadata = json.loads(data)
            return metadata
        else:
            print(error_message(res))
            return None

    def get_dummy_dataset(
        self,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[pd.DataFrame]:
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
        else:
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
        else:
            print(error_message(res))
            return None

    def estimate_smartnoise_cost(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
    ) -> Optional[dict[str, float]]:
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
        else:
            print(error_message(res))
            return None

    def opendp_query(
        self,
        opendp_pipeline: dp.Measurement,
        input_data_type: str = "df",
        fixed_delta: Optional[float] = None,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
        opendp_json = opendp_pipeline.to_json()
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "input_data_type": input_data_type,
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
                raise Exception(
                    "Not implemented: server should not return dataframes"
                )
                # Note: leaving this here. Support for opendp_polars
                # response_dict["query_response"] = polars.read_json(
                #    StringIO(response_dict["query_response"])
                # )

            return response_dict
        else:
            print(error_message(res))
            return None

    def estimate_opendp_cost(
        self,
        opendp_pipeline: dp.Measurement,
        input_data_type: str = "df",
        fixed_delta: Optional[float] = None,
    ) -> Optional[dict[str, float]]:
        opendp_json = opendp_pipeline.to_json()
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "input_data_type": input_data_type,
            "fixed_delta": fixed_delta,
        }
        res = self._exec("estimate_opendp_cost", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(error_message(res))
            return None

    def get_initial_budget(self) -> Optional[dict[str, float]]:
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_initial_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(error_message(res))
            return None

    def get_total_spent_budget(self) -> Optional[dict[str, float]]:
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_total_spent_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(error_message(res))
            return None

    def get_remaining_budget(self) -> Optional[dict[str, float]]:
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_remaining_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(error_message(res))
            return None

    def get_previous_queries(self) -> Optional[List[dict]]:
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_previous_queries", body_json)

        if res.status_code == 200:
            queries = json.loads(res.content.decode("utf8"))[
                "previous_queries"
            ]

            if not len(queries):
                return queries

            deserialised_queries = []
            for query in queries:
                match query["api"]:
                    case DPLibraries.SMARTNOISE_SQL:
                        pass
                    case DPLibraries.OPENDP:
                        opdp_query = make_load_json(query["query"])
                        query["query"] = opdp_query
                    case _:
                        raise ValueError(
                            "Cannot deserialise unknown query type:"
                            + f"{query['api']}"
                        )

                deserialised_queries.append(query)

            return deserialised_queries
        else:
            print(error_message(res))
            return None

    def _exec(self, endpoint: str, body_json: dict = {}) -> requests.Response:
        r = requests.post(
            self.url + "/" + endpoint, json=body_json, headers=self.headers
        )
        return r
