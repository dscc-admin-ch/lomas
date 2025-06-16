from diffprivlib_logger import serialise_pipeline
from returns.curry import partial
from returns.io import IOResultE
from returns.pipeline import flow
from returns.pointfree import map_
from sklearn.pipeline import Pipeline

from lomas_client.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
)
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response
from lomas_core.models.requests import (
    DiffPrivLibDummyQueryModel,
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse


class DiffPrivLibClient:
    """A client for executing and estimating the cost of DiffPrivLib queries."""

    def __init__(self, http_client: LomasHttpClient) -> None:
        self.http_client = http_client

    def cost(
        self,
        pipeline: Pipeline,
        feature_columns: list[str] = [""],
        target_columns: list[str] = [""],
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
    ) -> IOResultE[CostResponse]:
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
            target_columns (list[str], optional): the list of target column to predict
                May be None for certain models.
            test_size (float, optional): proportion of the test set
                Defaults to 0.2.
            test_train_split_seed (int, optional): seed for random train test split
                Defaults to 1.
            imputer_strategy (str, optional): imputation strategy. Defaults to "drop".
                "drop": will drop all rows with missing values
                "mean": will replace values by the mean of the column values
                "median": will replace values by the median of the column values
                "most_frequent": will replace values by the most frequent values

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        return flow(
            {
                "dataset_name": self.http_client.config.dataset_name,
                "diffprivlib_json": serialise_pipeline(pipeline),
                "feature_columns": feature_columns,
                "target_columns": target_columns,
                "test_size": test_size,
                "test_train_split_seed": test_train_split_seed,
                "imputer_strategy": imputer_strategy,
            },
            DiffPrivLibRequestModel.model_validate,
            partial(self.http_client.post, "estimate_diffprivlib_cost"),
            map_(lambda res: validate_model_response(self.http_client, res, CostResponse)),
        )

    def query(
        self,
        pipeline: Pipeline,
        feature_columns: list[str],
        target_columns: list[str] | None = None,
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> IOResultE[QueryResponse]:
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
            target_columns (list[str], optional): the list of target column to predict
                May be None for certain models.
            test_size (float, optional): proportion of the test set
                Defaults to 0.2.
            test_train_split_seed (int, optional): seed for random train test split
                Defaults to 1.
            imputer_strategy (str, optional): imputation strategy. Defaults to "drop".
                "drop": will drop all rows with missing values
                "mean": will replace values by the mean of the column values
                "median": will replace values by the median of the column values
                "most_frequent": : will replace values by the most frequent values
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.
                Defaults to DUMMY_SEED.

        Returns:
            Optional[Pipeline]: A trained DiffPrivLip pipeline
        """
        body_dict = {
            "dataset_name": self.http_client.config.dataset_name,
            "diffprivlib_json": serialise_pipeline(pipeline),
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }
        if dummy:
            return flow(
                {**body_dict, "dummy_nb_rows": nb_rows, "dummy_seed": seed},
                DiffPrivLibDummyQueryModel.model_validate,
                lambda body: self.http_client.post("dummy_diffprivlib_query", body),
                map_(lambda res: validate_model_response(self.http_client, res, QueryResponse)),
            )
        return flow(
            body_dict,
            DiffPrivLibQueryModel.model_validate,
            lambda body: self.http_client.post("diffprivlib_query", body),
            map_(lambda res: validate_model_response(self.http_client, res, QueryResponse)),
        )
