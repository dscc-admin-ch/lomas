import warnings

import numpy as np
import pandas as pd
from aio_pika.patterns.rpc import Proxy
from csvw_safe.metadata_structure import ColumnMetadata
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
        admin_database: Proxy,
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
        metadata = self.data_connector.metadata
        feature_metadata = [col for col in metadata.columns if col.name in feature_columns]

        first_step = self.dpl_pipeline.steps[0][1]

        # --- Handle feature constraints ---
        feature_bounds: tuple[list[float], list[float]] | None = None
        if hasattr(first_step, "data_norm"):

            def contribution(meta: ColumnMetadata) -> int:
                return 1 if meta.datatype == "boolean" else meta.maximum**2

            first_step.data_norm = np.sqrt(sum(contribution(meta) for meta in feature_metadata))

        if hasattr(first_step, "bounds") or hasattr(first_step, "bounds_X"):
            feature_bounds = get_dpl_bounds(feature_metadata)

        if hasattr(first_step, "bounds"):
            first_step.bounds = feature_bounds
        if hasattr(first_step, "bounds_X"):
            first_step.bounds_X = feature_bounds

        # --- Handle target constraints ---
        if hasattr(first_step, "bounds_y"):
            if not target_columns:
                raise InvalidQueryException("target_columns must be provided when bounds_y is required")
            target_metadata = [col for col in metadata.columns if col.name in target_columns]
            first_step.bounds_y = get_dpl_bounds(target_metadata)

    def fit_model_on_data(self, query_json: DiffPrivLibRequestModel) -> None:
        """
        Fit the DiffPrivLib pipeline on the dataset provided by the data connector.

        Steps:
            1. Validate inputs (no overlap between feature and target columns).
            2. Select and preprocess relevant columns (handle missing data).
            3. Split data into training and test sets.
            4. Deserialize the pipeline and inject server parameters.
            5. Fit the pipeline while treating PrivacyLeakWarning as an error.

        Args:
            query_json: Request object describing feature/target columns,
                        pipeline definition, and preprocessing options.

        Raises:
            InvalidQueryException: If feature/target columns overlap.
            ExternalLibraryException: If DiffPrivLib fitting fails.
        """
        # 1. Validate feature/target columns
        feature_columns = query_json.feature_columns.copy()
        target_columns = query_json.target_columns or []

        overlap = set(feature_columns) & set(target_columns)
        if overlap:
            raise InvalidQueryException(f"Columns cannot be both feature and target: {', '.join(overlap)}")

        # 2. Select and preprocess data
        useful_columns = feature_columns + target_columns
        df = self.data_connector.get_pandas_df()[useful_columns]
        df = handle_missing_data(df, query_json.imputer_strategy)

        # 3. Split data
        x_train, self.x_test, y_train, self.y_test = split_train_test_data(df, query_json)

        # 4. Deserialize and configure pipeline
        self.dpl_pipeline = deserialise_pipeline(query_json.diffprivlib_json)
        self.complete_pipeline(feature_columns, query_json.target_columns)

        # 5. Fit pipeline with strict warning handling
        warnings.simplefilter("error", PrivacyLeakWarning)
        try:
            y_train = None if y_train is None else y_train.to_numpy().ravel()
            self.dpl_pipeline = self.dpl_pipeline.fit(x_train, y_train)
        except PrivacyLeakWarning as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"PrivacyLeakWarning: {e} "
                + "Lomas server cannot fit pipeline on data, PrivacyLeakWarning is a blocker.",
            ) from e
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"Cannot fit pipeline on data because {e}",
            ) from e

    def cost(self, query_json: DiffPrivLibRequestModel) -> tuple[float, float]:
        """
        Estimate the privacy budget cost of running a DiffPrivLib query.

        Steps:
            1. Fit the model on the dataset (including accountant injection).
            2. Retrieve the total budget consumed from the accountant.

        Args:
            query_json: The request object describing the query (features, targets, pipeline JSON).

        Raises:
            ExternalLibraryException: If the pipeline fitting fails.

        Returns:
            A tuple of (epsilon, delta) costs.
        """
        # 1. Fit model (this will attach accountant and configure constraints)
        self.fit_model_on_data(query_json)

        # 2. Retrieve total budget
        epsilon, delta = self.accountant.total()
        return epsilon, delta

    def query(
        self,
        query_json: DiffPrivLibQueryModel,
    ) -> DiffPrivLibQueryResult:
        """
        Run the query on the fitted DiffPrivLib pipeline and return the results.

        Args:
            query_json: The request object describing the query parameters.

        Raises:
            InternalServerException: If `query` is called before `cost` (pipeline not initialized).
            ExternalLibraryException: If the underlying pipeline evaluation fails.

        Returns:
            DiffPrivLibQueryResult containing:
                - score: Model accuracy on the test set.
                - model: The trained DiffPrivLib pipeline.
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


def get_dpl_bounds(feature_columns: list[ColumnMetadata]) -> tuple[list[float], list[float]]:
    """
    Format metadata bounds of feature columns in format expected by DiffPrivLib.

    Args:
        - feature_columns (list[ColumnMetadata]): list of feature columns

    Return:
        tuple of lower and upper bounds as expected by DiffPrivLib
    """
    lower = [col.minimum if col.datatype != "boolean" else 0 for col in feature_columns]
    upper = [col.minimum if col.datatype != "boolean" else 1 for col in feature_columns]
    return (lower, upper)
