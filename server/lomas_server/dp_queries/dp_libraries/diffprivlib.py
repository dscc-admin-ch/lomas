from base64 import b64encode
import pickle
import warnings
from typing import Dict

from diffprivlib.utils import (
    DiffprivlibCompatibilityWarning,
    PrivacyLeakWarning,
)
from diffprivlib_logger import deserialise_pipeline
import pandas as pd
from sklearn.pipeline import Pipeline

from constants import DPLibraries
from dp_queries.dp_querier import DPQuerier
from dp_queries.dp_libraries.diffprivlib_utils import (
    handle_missing_data,
    split_train_test_data,
)
from utils.error_handler import ExternalLibraryException
from utils.input_models import DiffPrivLibInp
from utils.loggr import LOG

# DiffPrivLib warnings will trigger error
warnings.simplefilter("error", PrivacyLeakWarning)
warnings.simplefilter("error", DiffprivlibCompatibilityWarning)


class DiffPrivLibQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the DiffPrivLib library.
    """

    def fit_model_on_data(
        self, query_json: DiffPrivLibInp
    ) -> tuple[Pipeline, pd.DataFrame, pd.DataFrame]:
        """Perform necessary steps to fit the model on the data

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            fitted_dpl_pipeline (dpl model): the fitted model on the training data
            x_test (pd.DataFrame): test data feature
            y_test (pd.DataFrame): test data target
        """
        # Prepare data
        raw_data = self.private_dataset.get_pandas_df()
        data = handle_missing_data(raw_data, query_json.imputer_strategy)
        x_train, x_test, y_train, y_test = split_train_test_data(
            data, query_json
        )

        # Prepare DiffPrivLib pipeline
        dpl_pipeline = deserialise_pipeline(
            query_json.diffprivlib_json
        )
        LOG.error("*********************************************")
        LOG.error("query_json")
        LOG.error(query_json)
        LOG.error("*********************************************")
        LOG.error("dp pipeline")
        LOG.error(dpl_pipeline)
        LOG.error("x_train")
        LOG.error(x_train)
        LOG.error("y_train")
        LOG.error(y_train)

        # Fit the pipeline on the training set
        try:
            fitted_dpl_pipeline = dpl_pipeline.fit(x_train, y_train)
        except PrivacyLeakWarning as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"PrivacyLeakWarning: {e}. "
                + "Lomas server cannot fit pipeline on data, warning is a blocker.",
            ) from e
        except DiffprivlibCompatibilityWarning as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB,
                f"DiffprivlibCompatibilityWarning: {e}. "
                + "Lomas server cannot fit pipeline on data, warning is a blocker.",
            ) from e
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.DIFFPRIVLIB, "Cannot fit pipeline on data"
            ) from e

        return fitted_dpl_pipeline, x_test, y_test

    def cost(self, query_json: DiffPrivLibInp) -> tuple[float, float]:
        """Estimate cost of query

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        fitted_dpl_pipeline, _, _ = self.fit_model_on_data(query_json)

        # Compute budget
        spent_epsilon = 0.0
        spent_delta = 0.0
        for step in fitted_dpl_pipeline.steps:
            spent_epsilon += step[1].accountant.spent_budget[0][0]
            spent_delta += step[1].accountant.spent_budget[0][1]
        return spent_epsilon, spent_delta

    def query(self, query_json: DiffPrivLibInp) -> Dict:
        """Perform the query and return the response.

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InvalidQueryException: If the budget values are too small to
                perform the query.

        Returns:
            dict: The dictionary encoding of the resulting pd.DataFrame.
        """
        fitted_dpl_pipeline, x_test, y_test = self.fit_model_on_data(
            query_json
        )

        # Model accuracy
        score = fitted_dpl_pipeline.score(x_test, y_test)

        # Serialise model
        pickled_model = b64encode(pickle.dumps(fitted_dpl_pipeline))

        query_response = {
            "score": score,
            "model": pickled_model.decode("utf-8"),
        }
        return query_response
