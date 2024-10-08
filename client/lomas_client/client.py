import base64
import json
import pickle
from typing import Dict, List, Optional, Type, Union

import opendp as dp
import pandas as pd
import requests
from diffprivlib_logger import serialise_pipeline
from fastapi import status
from lomas_client.http_client import LomasHttpClient
from lomas_client.libraries.smartnoise_sql import SmartnoiseSQLClient
from lomas_client.libraries.opendp import OpenDPClient
from lomas_core.constants import DPLibraries
from lomas_core.models.requests import (
    DiffPrivLibDummyQueryModel,
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
    GetDsData,
    GetDummyDataset,
    LomasRequestModel,
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
    SmartnoiseSQLDummyQueryModel,
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
    SmartnoiseSynthDummyQueryModel,
    SmartnoiseSynthQueryModel,
    SmartnoiseSynthRequestModel,
)
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json
from pydantic import BaseModel
from sklearn.pipeline import Pipeline
from smartnoise_synth_logger import serialise_constraints

from lomas_client.constants import (
    CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DIFFPRIVLIB_READ_TIMEOUT,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    SMARTNOISE_SYNTH_READ_TIMEOUT,
    SNSYNTH_DEFAULT_SAMPLES_NB,
)
from lomas_client.utils import (
    InternalClientException,
    raise_error,
    validate_synthesizer,
)
from lomas_core.models.responses import CostResponse, DummyDsResponse, QueryResponse

# Opendp_logger
enable_logging()
enable_features("contrib")


class Client:
    """Client class to send requests to the server.

    Handle all serialisation and deserialisation steps
    """

    def __init__(self, url: str, user_name: str, dataset_name: str) -> None:
        """Initializes the Client with the specified URL, user name, and dataset name.

        Args:
            url (str): The base URL for the API server.
            user_name (str): The name of the user allowed to perform queries.
            dataset_name (str): The name of the dataset to be accessed or manipulated.
        """
        
        self.http_client = LomasHttpClient(url, user_name, dataset_name)
        self.smartnoise_sql = SmartnoiseSQLClient(self.http_client)
        self.opendp= OpenDPClient(self.http_client)


    def get_dataset_metadata(
        self,
    ) -> Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
        """This function retrieves metadata for the dataset.

        Returns:
            Optional[Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]]:
                A dictionary containing dataset metadata.
        """
        body_dict = {"dataset_name": self.http_client.dataset_name}
        body = GetDsData.model_validate(body_dict)
        res = self.http_client.post(
            "get_dataset_metadata", body
        )
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
        body_dict = {
                "dataset_name": self.http_client.dataset_name,
                "dummy_nb_rows": nb_rows,
                "dummy_seed": seed,
            }
        body = GetDummyDataset.model_validate(body_dict)
        res = self.http_client.post(
            "get_dummy_dataset", body
        )

        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            res_model = DummyDsResponse.model_validate_json(data)
            return res_model.dummy_df

        raise_error(res)
        return None

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
        """Trains a DiffPrivLib pipeline and return a trained Pipeline.

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
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": serialise_pipeline(pipeline),
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }

        request_model: Type[DiffPrivLibRequestModel]
        if dummy:
            endpoint = "dummy_diffprivlib_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
            request_model = DiffPrivLibDummyQueryModel
        else:
            endpoint = "diffprivlib_query"
            request_model = DiffPrivLibQueryModel

        res = self._exec(
            endpoint, body_json, request_model, read_timeout=DIFFPRIVLIB_READ_TIMEOUT
        )
        if res.status_code == status.HTTP_200_OK:
            response = res.json()
            model = base64.b64decode(response["query_response"]["model"])
            response["query_response"]["model"] = pickle.loads(model)
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
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": serialise_pipeline(pipeline),
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }
        res = self._exec(
            "estimate_diffprivlib_cost",
            body_json,
            DiffPrivLibRequestModel,
            read_timeout=DIFFPRIVLIB_READ_TIMEOUT,
        )

        if res.status_code == status.HTTP_200_OK:
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
        
        body_dict = {
                "dataset_name": self.http_client.dataset_name
            }
        
        body = GetDsData.model_validate(body_dict)
        res = self.http_client.post(
            "get_initial_budget", body
        )

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        raise_error(res)
        return None

    def get_total_spent_budget(self) -> Optional[dict[str, float]]:
        """This function retrieves the total spent budget.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the total spent budget.
        """
        body_dict = {
                "dataset_name": self.http_client.dataset_name
            }
        
        body = GetDsData.model_validate(body_dict)
        res = self.http_client.post(
            "get_total_spent_budget", body
        )

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        raise_error(res)
        return None

    def get_remaining_budget(self) -> Optional[dict[str, float]]:
        """This function retrieves the remaining budget.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the remaining budget.
        """
        body_dict = {
                "dataset_name": self.http_client.dataset_name
            }
        
        body = GetDsData.model_validate(body_dict)
        res = self.http_client.post(
            "get_remaining_budget", body
        )

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
        body_dict = {
                "dataset_name": self.http_client.dataset_name
            }
        
        body = GetDsData.model_validate(body_dict)
        res = self.http_client.post(
            "get_previous_queries", body
        )

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

    
