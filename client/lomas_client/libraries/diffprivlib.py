from typing import List, Optional, Type

from diffprivlib_logger import serialise_pipeline
from lomas_core.models.requests import (
    DiffPrivLibDummyQueryModel,
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse
from sklearn.pipeline import Pipeline

from lomas_client.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
)
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response


class DiffPrivLibClient:
    """A client for executing and estimating the cost of DiffPrivLib queries."""

    def __init__(self, http_client: LomasHttpClient):
        self.http_client = http_client

    def cost(
        self,
        pipeline: Pipeline,
        feature_columns: List[str] = [""],
        target_columns: List[str] = [""],
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
    ) -> Optional[CostResponse]:
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
        body_dict = {
            "dataset_name": self.http_client.dataset_name,
            "diffprivlib_json": serialise_pipeline(pipeline),
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }

        body = DiffPrivLibRequestModel.model_validate(body_dict)
        res = self.http_client.post("estimate_diffprivlib_cost", body)

        return validate_model_response(res, CostResponse)

    def query(
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
    ) -> Optional[QueryResponse]:
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
        body_dict = {
            "dataset_name": self.http_client.dataset_name,
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
            body_dict["dummy_nb_rows"] = nb_rows
            body_dict["dummy_seed"] = seed
            request_model = DiffPrivLibDummyQueryModel
        else:
            endpoint = "diffprivlib_query"
            request_model = DiffPrivLibQueryModel

        body = request_model.model_validate(body_dict)
        res = self.http_client.post(endpoint, body)

        return validate_model_response(res, QueryResponse)
