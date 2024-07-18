import base64
import json
from enum import StrEnum
from io import StringIO
from typing import Dict, List, Optional, OrderedDict, Union

import opendp as dp
import pandas as pd
import polars as pl
import requests
from diffprivlib_logger import serialise_pipeline
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json
from sklearn.pipeline import Pipeline

# Opendp_logger
enable_logging()
enable_features("contrib")

# Client constants: may be modified
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42
HTTP_200_OK = 200


class DPLibraries(StrEnum):
    """Enum of the DP librairies used in the server
    WARNING: MUST match those of lomas_server
    """

    SMARTNOISE_SQL = "smartnoise_sql"
    OPENDP = "opendp"
    DIFFPRIVLIB = "diffprivlib"


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

    metadata = None

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

    def get_df_dtypes(self) -> Dict[str, type]:
        """
        Returns the pandas dictionary for the dataframe types of the dataset.

        Returns:
            Dict[str, type]: The dtypes dictionary
        """
        metadata = self.get_dataset_metadata()
        dtypes = {}
        for col_name, data in metadata["columns"].items():
            if data["type"] in ["int", "float"]:
                dtypes[col_name] = f"{data['type']}{data['precision']}"
            else:
                dtypes[col_name] = data["type"]

        return dtypes

    def get_dataset_metadata(
        self,
    ) -> Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
        """This function retrieves metadata for the dataset.

        Returns:
            Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
                A dictionary containing dataset metadata.
        """
        if self.metadata is None:
            res = self._exec(
                "get_dataset_metadata", {"dataset_name": self.dataset_name}
            )
            if res.status_code == HTTP_200_OK:
                data = res.content.decode("utf8")
                self.metadata = json.loads(data)

                return self.metadata

            print(error_message(res))
            return None
        else:
            return self.metadata

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

        if res.status_code == HTTP_200_OK:
            data = res.content.decode("utf8")
            dtypes = self.get_df_dtypes()
            df = pd.read_csv(StringIO(data), dtype=dtypes)
            return df
        print(error_message(res))
        return None

    def get_dummy_lf(
        self, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED
    ) -> Optional[pl.LazyFrame]:
        """
        Returns the polars LazyFrame for the dummy dataset with
        optional parameters.

        Args:
            nb_rows (int, optional): The number of rows in the dummy dataset.

                Defaults to DUMMY_NB_ROWS.

            seed (int, optional): The random seed for generating the dummy dataset.

                Defaults to DUMMY_SEED.

        Returns:
            Optional[pl.LazyFrame]: The LazyFrame for the dummy dataset
        """
        dummy_pandas = self.get_dummy_dataset(nb_rows=nb_rows, seed=seed)

        if dummy_pandas is None:
            return None
        return pl.from_pandas(dummy_pandas).lazy()

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

        if res.status_code == HTTP_200_OK:
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

        if res.status_code == HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))
        print(error_message(res))
        return None

    def _get_opendp_request_body(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        delta: Optional[float] = None,
        mechanism: Optional[str] = "Laplace",
        output_measure_type_arg: Optional[str] = "float64",
    ):
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.\
                Can be a dp.Measurement or a polars LazyFrame (plan) for opendp.polars\
                pipelines.
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).
                In that case a delta must be provided by the user.
                Defaults to None.
            mechanism: (str, optional): Type of noise addition mechanism to use\
                in polars pipelines. "Laplace" or "Gaussian".
            output_measure_type_arg: (str, optional): Type argument for the output measure.
                Usually "float64" for continuous noise or "int32" for discrete noise.
        
        Raises:
            Exception: If the opendp_pipeline type is not supported.

        Returns:
            dict: A dictionnary for the request body.
        """
        body_json = {
            "dataset_name": self.dataset_name,
            "delta": delta,
            "mechanism": mechanism,
            "output_measure_type_arg": output_measure_type_arg,
        }

        if isinstance(opendp_pipeline, dp.Measurement):
            body_json["opendp_json"] = opendp_pipeline.to_json()
            body_json["pipeline_type"] = "legacy"
        elif isinstance(opendp_pipeline, pl.LazyFrame):
            body_json["opendp_json"] = opendp_pipeline.serialize()
            body_json["pipeline_type"] = "polars"
        else:
            raise Exception(
                f"Opendp_pipeline must either of type Measurement"
                f" or LazyFrame, found {type(opendp_pipeline)}"
            )

        return body_json

    def opendp_query(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        delta: Optional[float] = None,
        mechanism: Optional[str] = "Laplace",
        output_measure_type_arg: Optional[str] = "float64",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.\
                Can be a dp.Measurement or a polars LazyFrame (plan) for opendp.polars\
                pipelines.
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).
                In that case a delta must be provided by the user.
                Defaults to None.
            mechanism: (str, optional): Type of noise addition mechanism to use\
                in polars pipelines. "Laplace" or "Gaussian".
            output_measure_type_arg: (str, optional): Type argument for the output measure.
                Usually "float64" for continuous noise or "int32" for discrete noise.
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
            Defaults to DUMMY_SEED.

        Raises:
            Exception: If the opendp_pipeline type is not suppported.

        Returns:
            Optional[dict]: A dictionary of the response body\
                containing the deserialized pipeline result.
        """
        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            delta=delta,
            mechanism=mechanism,
            output_measure_type_arg=output_measure_type_arg,
        )
        if dummy:
            endpoint = "dummy_opendp_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "opendp_query"

        res = self._exec(endpoint, body_json)
        if res.status_code == HTTP_200_OK:
            data = res.content.decode("utf8")
            response_dict = json.loads(data)

            # Opendp outputs can be single numbers or dataframes,
            # we handle the latter here.
            # This is a hack for now, maybe use parquet to send results over.
            if isinstance(response_dict["query_response"], str):
                response_dict["query_response"] = pl.read_json(
                    StringIO(response_dict["query_response"])
                )

            return response_dict

        print(error_message(res))
        return None

    def estimate_opendp_cost(
        self,
        opendp_pipeline: dp.Measurement,
        mechanism: Optional[str] = "Laplace",
        output_measure_type_arg: Optional[str] = "float64",
        delta: Optional[float] = None,
    ) -> Optional[dict[str, float]]:
        """This function estimates the cost of executing an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.
            mechanism: (str, optional): Type of noise addition mechanism to use\
                in polars pipelines. "Laplace" or "Gaussian".
            output_measure_type_arg: (str, optional): Type argument for the output measure.
                Usually "float64" for continuous noise or "int32" for discrete noise.
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.\
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).\
                In that case a delta must be provided by the user.\
                Defaults to None.

        Raises:
            Exception: If the opendp_pipeline type is not supported.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            delta=delta,
            mechanism=mechanism,
            output_measure_type_arg=output_measure_type_arg,
        )
        res = self._exec("estimate_opendp_cost", body_json)

        if res.status_code == HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        print(error_message(res))
        return None

    def get_lf_seed(self):
        """
        Get the LazyFrame seed for OpenDP polars pipelines

        Raises:
            Exception: If some column type is not supported by polars or\
                if some information is missing from the metadata.

        Returns:
            pl.LazyFrame: The polars LazyFrame seed for an OpenDP polars pipeline.
        """
        metadata = self.get_dataset_metadata()
        schema = OrderedDict()
        for name, series_info in metadata["columns"].items():
            if "type" not in series_info:
                raise Exception("Missing type info in metadata")
            try:
                if series_info["type"] in ["float", "int"]:
                    dtype = f"{series_info['type']}{series_info['precision']}"
                else:
                    dtype = series_info["type"]

                series_type = {
                    "int32": pl.datatypes.Int32,
                    "float32": pl.datatypes.Float32,
                    "int64": pl.datatypes.Int64,
                    "float64": pl.datatypes.Float64,
                    "string": pl.datatypes.String,
                    "boolean": pl.datatypes.Boolean,
                }[dtype]
            except Exception as _:
                raise Exception(
                    f"Type {series_info['type']} not supported by OpenDP."
                )

            schema[name] = series_type

        return pl.DataFrame(None, schema, orient="row").lazy()

    def diffprivlib_query(
        self,
        pipeline: Pipeline,
        feature_columns: List[str],
        target_columns: Optional[List[str]] = None,
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Pipeline:
        """This function trains a DiffPrivLib pipeline on the sensitive data
        and return a trained Pipeline.

        Args:
            pipeline (sklearn.pipeline): DiffPrivLib pipeline with three conditions:
                - The pipeline MUST start with a `models.StandardScaler`.
                  Otherwise a PrivacyLeakWarning is raised by DiffPrivLib library and
                  is treated as an error in lomas server.
                - `random_state` fields can only be int (`RandomState` will not work).
                - `accountant` fields must be None.
                Note: as in DiffPrivLib, avoid any DiffprivlibCompatibilityWarning
                to ensure that the pipeline does what is intended.
            feature_columns (list[str]): the list of feature column to train
            target_columns (list[str], optional): the list of target column to predict \
                May be None for certain models.
            test_size (float, optional): proportion of the test set \
                Defaults to 0.2.
            test_train_split_seed (int, optional): seed for random train test split \
                Defaults to 1.
            imputer_strategy (str, optional): imputation strategy. Defaults to "drop".
                "drop": will drop all rows with missing values
                "mean": will replace values by the mean of the column values
                "median": will replace values by the median of the column values
                "most_frequent": : will replace values by the most frequent values
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
                Defaults to DUMMY_SEED.

        Returns:
            Optional[Pipeline]: A trained DiffPrivLip pipeline
        """
        dpl_json = serialise_pipeline(pipeline)
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": dpl_json,
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }
        if dummy:
            endpoint = "dummy_diffprivlib_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "diffprivlib_query"

        res = self._exec(endpoint, body_json)
        if res.status_code == HTTP_200_OK:
            response = res.json()
            model = base64.b64decode(response["query_response"]["model"])
            response["query_response"]["model"] = json.loads(model)
            return response
        print(
            f"Error while processing DiffPrivLib request in server \
                status code: {res.status_code} message: {res.text}"
        )
        return res.text

    def estimate_diffprivlib_cost(
        self,
        pipeline: Pipeline,
        feature_columns: List[str] = [""],
        target_columns: List[str] = [""],
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
    ) -> dict:
        """This function estimates the cost of executing a DiffPrivLib query.

        Args:
            pipeline (sklearn.pipeline): DiffPrivLib pipeline with three conditions:
                - The pipeline MUST start with a `models.StandardScaler`.
                  Otherwise a PrivacyLeakWarning is raised by DiffPrivLib library and
                  is treated as an error in lomas server.
                - `random_state` fields can only be int (`RandomState` will not work).
                - `accountant` fields must be None.
                Note: as in DiffPrivLib, avoid any DiffprivlibCompatibilityWarning
                to ensure that the pipeline does what is intended.
            feature_columns (list[str]): the list of feature column to train
            target_columns (list[str], optional): the list of target column to predict \
                May be None for certain models.
            test_size (float, optional): proportion of the test set \
                Defaults to 0.2.
            test_train_split_seed (int, optional): seed for random train test split \
                Defaults to 1.
            imputer_strategy (str, optional): imputation strategy. Defaults to "drop".
                "drop": will drop all rows with missing values
                "mean": will replace values by the mean of the column values
                "median": will replace values by the median of the column values
                "most_frequent": : will replace values by the most frequent values

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        dpl_json = serialise_pipeline(pipeline)
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": dpl_json,
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }
        res = self._exec("estimate_diffprivlib_cost", body_json)

        if res.status_code == HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))
        print(
            f"Error while executing provided query in server:\n"
            f"status code: {res.status_code} message: {res.text}"
        )
        return res.text

    def get_initial_budget(self) -> Optional[dict[str, float]]:
        """This function retrieves the initial budget.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the initial budget.
        """
        body_json = {
            "dataset_name": self.dataset_name,
        }
        res = self._exec("get_initial_budget", body_json)

        if res.status_code == HTTP_200_OK:
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

        if res.status_code == HTTP_200_OK:
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

        if res.status_code == HTTP_200_OK:
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

        if res.status_code == HTTP_200_OK:
            queries = json.loads(res.content.decode("utf8"))[
                "previous_queries"
            ]

            if not queries:
                return queries

            deserialised_queries = []
            for query in queries:
                match query["dp_library"]:
                    case DPLibraries.SMARTNOISE_SQL:
                        pass
                    case DPLibraries.OPENDP:
                        opdp_query = make_load_json(
                            query["client_input"]["opendp_json"]
                        )
                        query["client_input"]["opendp_json"] = opdp_query
                    case DPLibraries.DIFFPRIVLIB:
                        model = base64.b64decode(
                            query["response"]["query_response"]["model"]
                        )
                        query["response"]["query_response"]["model"] = (
                            json.loads(model)
                        )
                    case _:
                        raise ValueError(
                            "Cannot deserialise unknown query type:"
                            + f"{query['dp_library']}"
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
