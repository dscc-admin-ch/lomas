import warnings

import numpy as np
import pandas as pd
from diffprivlib import BudgetAccountant
from diffprivlib.utils import PrivacyLeakWarning
from diffprivlib_logger import deserialise_pipeline
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.models.requests import (
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
)
from lomas_core.models.responses import DiffPrivLibQueryResult
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_libraries.utils import (
    handle_missing_data,
)
from lomas_server.dp_queries.dp_querier import DPQuerier


class DiffPrivLibQuerier(DPQuerier[DiffPrivLibRequestModel, DiffPrivLibQueryModel, DiffPrivLibQueryResult]):
    """Concrete implementation of the DPQuerier ABC for the DiffPrivLib library."""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: AdminDatabase,
    ) -> None:
        super().__init__(data_connector, admin_database)
        self.dpl_pipeline: Pipeline | None = None
        self.x_test: pd.DataFrame | None = None
        self.y_test: pd.DataFrame | None = None
        self.accountant = BudgetAccountant()

    def complete_pipeline(self, feature_columns: list[str], target_columns: list[str] | None) -> None:
        """
        Finalize the DiffPrivLib pipeline by injecting accountant and privacy constraints.

        Steps:
            1. Attach the shared budget accountant to all compatible steps.
            2. Add metadata-driven privacy constraints (`data_norm`, `bounds`, `bounds_X`, `bounds_y`)
            to the first pipeline step when supported.

        Args:
            feature_columns: List of feature columns used for training.
            target_columns: Optional list of target columns (required if `bounds_y` is needed).

        Raises:
            InternalServerException: If pipeline is not initialized.
            InvalidQueryException: If target bounds are required but not provided.
        """
        if self.dpl_pipeline is None:
            raise InternalServerException("Pipeline must be initialized before calling complete_pipeline")

        # 1. Add budget accountant
        for _, step in self.dpl_pipeline.steps:
            if hasattr(step, "accountant"):
                step.accountant = self.accountant

        # 2. Get metadata for features
        columns_metadata = self.data_connector.get_metadata().model_dump()["columns"]
        feature_metadata = {col: columns_metadata[col] for col in feature_columns}

        first_step = self.dpl_pipeline.steps[0][1]

        # --- Handle feature constraints ---
        feature_bounds: tuple[list[float], list[float]] | None = None
        if hasattr(first_step, "data_norm"):
            first_step.data_norm = np.sqrt(sum(meta["upper"] ** 2 for meta in feature_metadata.values()))

        if hasattr(first_step, "bounds") or hasattr(first_step, "bounds_X"):
            feature_bounds = get_dpl_bounds(feature_metadata, feature_columns)

        if hasattr(first_step, "bounds"):
            first_step.bounds = feature_bounds
        if hasattr(first_step, "bounds_X"):
            first_step.bounds_X = feature_bounds

        # --- Handle target constraints ---
        if hasattr(first_step, "bounds_y"):
            if not target_columns:
                raise InvalidQueryException("target_columns must be provided when bounds_y is required")
            target_metadata = {col: columns_metadata[col] for col in target_columns}
            first_step.bounds_y = get_dpl_bounds(target_metadata, feature_columns=target_columns)

    def fit_model_on_data(self, query_json: DiffPrivLibRequestModel) -> None:
        """Perform necessary steps to fit the model on the data.

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
        """
        # Prepare data
        df = self.data_connector.get_pandas_df()

        # Check for overlap
        useful_columns = query_json.feature_columns.copy()
        if query_json.target_columns is not None:
            for target in query_json.target_columns:
                if target in query_json.feature_columns:
                    raise InvalidQueryException(
                        f"A column may only be in one of features and target. {target} is in both."
                    )
                useful_columns.append(target)

        df = df[useful_columns]
        data = handle_missing_data(df, query_json.imputer_strategy)
        x_train, self.x_test, y_train, self.y_test = split_train_test_data(data, query_json)

        # Prepare DiffPrivLib pipeline
        self.dpl_pipeline = deserialise_pipeline(query_json.diffprivlib_json)

        # Add arguments and parameters to the pipeline
        self.complete_pipeline(query_json.feature_columns, query_json.target_columns)

        # Fit the pipeline on the training set
        warnings.simplefilter("error", PrivacyLeakWarning)
        try:
            if y_train is not None:
                y_train = y_train.to_numpy().ravel()
            self.dpl_pipeline = self.dpl_pipeline.fit(x_train, y_train)
        except PrivacyLeakWarning as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"PrivacyLeakWarning: {e} "
                + "Lomas server cannot fit pipeline on data, "
                + "PrivacyLeakWarning is a blocker.",
            ) from e
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"Cannot fit pipeline on data because {e}",
            ) from e

    def cost(self, query_json: DiffPrivLibRequestModel) -> tuple[float, float]:
        """Estimate cost of query.

        Args:
            query_json (DiffPrivLibRequestModel): The request model object.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        self.fit_model_on_data(query_json)
        spent_budget = self.accountant.total()
        return spent_budget[0], spent_budget[1]

    def query(
        self,
        query_json: DiffPrivLibQueryModel,
    ) -> DiffPrivLibQueryResult:
        """Perform the query and return the response.

        Args:
            query_json (DiffPrivLibQueryModel): The request model object.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InvalidQueryException: If the budget values are too small to
                perform the query.

        Returns:
            dict: The dictionary encoding of the resulting pd.DataFrame.
        """
        if self.dpl_pipeline is None:
            raise InternalServerException("DiffPrivLib `query` method called before `cost` method")

        # Model accuracy
        score = self.dpl_pipeline.score(self.x_test, self.y_test)

        # Serialise model
        return DiffPrivLibQueryResult(score=score, model=self.dpl_pipeline)


def split_train_test_data(
    df: pd.DataFrame, query_json: DiffPrivLibRequestModel
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split the data between train and test set.

    Args:
        df (pd.DataFrame): dataframe with the data
        query_json (DiffPrivLibRequestModel): user input query indication
            feature_columns (list[str]): columns from data to use as features
            target_columns (list[str]): columns from data to use as target (to predict)
            test_size (float): proportion of data in the test set
            test_train_split_seed (int): seed for the random train-test split

    Returns:
        x_train (pd.DataFrame): training data features
        x_test (pd.DataFrame): testing data features
        y_train (pd.DataFrame): training data target
        y_test (pd.DataFrame): testing data target
    """
    feature_data = df[query_json.feature_columns]

    if query_json.target_columns is None:
        x_train, x_test = train_test_split(
            feature_data,
            test_size=query_json.test_size,
            random_state=query_json.test_train_split_seed,
        )
        y_train, y_test = None, None
    else:
        label_data = df[query_json.target_columns]
        x_train, x_test, y_train, y_test = train_test_split(
            feature_data,
            label_data,
            test_size=query_json.test_size,
            random_state=query_json.test_train_split_seed,
        )
    return x_train, x_test, y_train, y_test


def get_dpl_bounds(columns_metadata: dict, feature_columns: list[str]) -> tuple[list[float], list[float]]:
    """
    Format metadata bounds of feature columns in format expected by DiffPrivLib.

    Args:
        - columns_metadata: metadata
        - feature_columns (list[str]): list of feature columns

    Return:
        tuple of lower and upper bounds as expected by DiffPrivLib
    """
    lower = [columns_metadata[col]["lower"] for col in feature_columns]
    upper = [columns_metadata[col]["upper"] for col in feature_columns]
    return (lower, upper)
