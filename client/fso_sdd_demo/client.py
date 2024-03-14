import requests
import json
import pandas as pd
from io import StringIO
from opendp_logger import enable_logging
from opendp.mod import enable_features

from fso_sdd_demo.serialiser import serialize_diffprivlib

# Note: leaving this here. Support for opendp_polars
# import polars

# Opendp_logger
enable_logging()
enable_features("contrib")

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42


class Client:
    def __init__(self, url, user_name: str, dataset_name: str):
        self.url = url
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.headers["user-name"] = user_name
        self.dataset_name = dataset_name

    def get_dataset_metadata(
        self,
    ) -> dict:
        res = self._exec(
            "get_dataset_metadata", {"dataset_name": self.dataset_name}
        )
        if res.status_code == 200:
            data = res.content.decode("utf8")
            metadata = json.loads(data)

            return metadata
        else:
            print(
                f"Error while getting dataset metadata in server \
                    status code: {res.status_code} message: {res.text}"
            )
        return res.text

    def get_dummy_dataset(
        self,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> pd.DataFrame:
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
            print(
                f"Error while creating dummy dataset in server \
                    status code: {res.status_code} message: {res.text}"
            )
        return res.text

    def smartnoise_query(
        self,
        query,
        epsilon: float,
        delta: float,
        mechanisms: dict = {},
        postprocess: bool = True,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> pd.DataFrame:
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
            print(
                f"Error while executing provided query in server:\n"
                f" status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def estimate_smartnoise_cost(
        self,
        query,
        epsilon: float,
        delta: float,
        mechanisms: dict = {},
    ) -> dict:
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
            print(
                f"Error while executing provided query in server:\n"
                f"status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def opendp_query(
        self,
        opendp_pipeline,
        input_data_type: str = "df",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> pd.DataFrame:
        opendp_json = opendp_pipeline.to_json()
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "input_data_type": input_data_type,
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
            print(
                f"Error while processing OpenDP request in server \
                    status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def estimate_opendp_cost(
        self,
        opendp_pipeline,
        input_data_type="df",
    ) -> dict:
        opendp_json = opendp_pipeline.to_json()
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "input_data_type": input_data_type,
        }
        res = self._exec("estimate_opendp_cost", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(
                f"Error while executing provided query in server:\n"
                f"status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def diffprivlib_query(
        self,
        pipeline,
        target_column: str = "",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> pd.DataFrame:
        dpl_json_str = serialize_diffprivlib(pipeline)
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": dpl_json_str,
            "target_column": target_column,
        }
        if dummy:
            endpoint = "dummy_diffprivlib_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "diffprivlib_query"

        res = self._exec(endpoint, body_json)
        if res.status_code == 200:
            data = res.content.decode("utf8")
            response_dict = json.loads(data)
            return response_dict
        else:
            print(
                f"Error while processing DiffPrivLib request in server \
                    status code: {res.status_code} message: {res.text}"
            )
            return res.text

    # def estimate_diffprivlib_cost(
    #     self,
    #     pipeline,
    #     y_column: str = "",
    # ) -> dict:
    #     dpl_json_str = serialize_diffprivlib(pipeline)
    #     body_json = {
    #         "dataset_name": self.dataset_name,
    #         "diffprivlib_json": dpl_json_str,
    #         "y_column": y_column,
    #     }
    #     res = self._exec("estimate_diffprivlib_cost", body_json)

    #     if res.status_code == 200:
    #         return json.loads(res.content.decode("utf8"))
    #     else:
    #         print(
    #             f"Error while executing provided query in server:\n"
    #             f"status code: {res.status_code} message: {res.text}"
    #         )
    #         return res.text

    def get_initial_budget(self):
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_initial_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(
                f"Error while fetching total budget \
                    status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def get_total_spent_budget(self):
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_total_spent_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(
                f"Error while fetching total spent budget \
                    status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def get_remaining_budget(self):
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_remaining_budget", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(
                f"Error while fetching remaining budget \
                    status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def get_previous_queries(self):
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_previous_queries", body_json)

        if res.status_code == 200:
            return json.loads(res.content.decode("utf8"))
        else:
            print(
                f"Error while fetching previous queries \
                    status code: {res.status_code} message: {res.text}"
            )
            return res.text

    def _exec(self, endpoint, body_json: dict = {}):
        r = requests.post(
            self.url + "/" + endpoint, json=body_json, headers=self.headers
        )
        return r
