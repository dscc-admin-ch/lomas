import warnings
from typing import Optional

import pandas as pd
from diffprivlib.utils import PrivacyLeakWarning
from diffprivlib_logger import deserialise_pipeline
from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
)
from lomas_core.models.requests import (
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
)
from lomas_core.models.responses import DiffPrivLibQueryResult
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_libraries.utils import (
    handle_missing_data,
)
from lomas_server.dp_queries.dp_querier import DPQuerier


class DiffPrivLibQuerier(
    DPQuerier[DiffPrivLibRequestModel, DiffPrivLibQueryModel, DiffPrivLibQueryResult]
):
    """Concrete implementation of the DPQuerier ABC for the DiffPrivLib library."""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: AdminDatabase,
    ) -> None:
        super().__init__(data_connector, admin_database)
        self.dpl_pipeline: Optional[Pipeline] = None
        self.x_test: Optional[pd.DataFrame] = None
        self.y_test: Optional[pd.DataFrame] = None

    def fit_model_on_data(
        self, query_json: DiffPrivLibRequestModel
    ) -> tuple[Pipeline, pd.DataFrame, pd.DataFrame]:
        """Perform necessary steps to fit the model on the data.

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            dpl_pipeline (dpl model): the fitted model on the training data
            x_test (pd.DataFrame): test data feature
            y_test (pd.DataFrame): test data target
        """
        # Prepare data
        raw_data = self.data_connector.get_pandas_df()
        data = handle_missing_data(raw_data, query_json.imputer_strategy)
        x_train, x_test, y_train, y_test = split_train_test_data(data, query_json)

        # Prepare DiffPrivLib pipeline
        dpl_pipeline = deserialise_pipeline(query_json.diffprivlib_json)

        # Fit the pipeline on the training set
        warnings.simplefilter("error", PrivacyLeakWarning)
        try:
            if y_train is not None:
                y_train = y_train.values.ravel()
            dpl_pipeline = dpl_pipeline.fit(x_train, y_train)
        except PrivacyLeakWarning as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"PrivacyLeakWarning: {e}. "
                + "Lomas server cannot fit pipeline on data, "
                + "PrivacyLeakWarning is a blocker.",
            ) from e
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"Cannot fit pipeline on data because {e}",
            ) from e

        return dpl_pipeline, x_test, y_test

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
        self.dpl_pipeline, self.x_test, self.y_test = self.fit_model_on_data(query_json)

        # Compute budget
        spent_epsilon = 0.0
        spent_delta = 0.0
        for step in self.dpl_pipeline.steps:
            spent_epsilon += step[1].accountant.spent_budget[0][0]
            spent_delta += step[1].accountant.spent_budget[0][1]
        return spent_epsilon, spent_delta

    def query(
        self,
        query_json: DiffPrivLibQueryModel,  # pylint: disable=unused-argument
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
            raise InternalServerException(
                "DiffPrivLib `query` method called before `cost` method"
            )

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
