import json
import os
import unittest
from io import StringIO
import warnings

from diffprivlib import models
from diffprivlib.utils import (
    DiffprivlibCompatibilityWarning,
    PrivacyLeakWarning,
)
from diffprivlib_logger import serialise_pipeline
import opendp.prelude as dp_p
import pandas as pd
from fastapi import status
from fastapi.testclient import TestClient
from opendp.mod import enable_features
from opendp_logger import enable_logging
from pymongo.database import Database
from sklearn.pipeline import Pipeline
from tests.test_api import TestRootAPIEndpoint

from admin_database.utils import database_factory, get_mongodb
from app import app
from constants import EPSILON_LIMIT, DatasetStoreType, DPLibraries
from mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)
from tests.constants import (
    ENV_MONGO_INTEGRATION,
    ENV_S3_INTEGRATION,
    TRUE_VALUES,
)
from utils.config import CONFIG_LOADER
from utils.error_handler import InternalServerException
from utils.example_inputs import (
    example_diffprivlib,
    example_dummy_diffprivlib,
)
from utils.loggr import LOG

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005

enable_features("floating-point")


class TestDiffPrivLibEndpoint(TestRootAPIEndpoint):  # pylint: disable=R0904
    """
    End-to-end tests of the api endpoints.

    This test can be both executed as an integration test
    (enabled by setting LOMAS_TEST_MONGO_INTEGRATION to True),
    or a standard test. The first requires a mongodb to be started
    before running while the latter will use a local YamlDatabase.
    """

    def test_diffprivlib_query(self) -> None:
        """Test diffprivlib query"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/diffprivlib_query",
                json=example_diffprivlib,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["query_response"]["score"] >= 0
            assert response_dict["query_response"]["model"]
            assert response_dict["spent_epsilon"] > 0
            assert response_dict["spent_delta"] == 0
            
            # # Should work for different imputation strategy (but does not yet #255)
            diffprivlib_body = dict(example_diffprivlib)
            # diffprivlib_body["imputer_strategy"] = "mean"
            # response = client.post(
            #     "/diffprivlib_query",
            #     json=diffprivlib_body,
            #     headers=self.headers,
            # )
            # LOG.error(response)
            # response_dict = json.loads(response.content.decode("utf8"))
            # LOG.error(response_dict)
            # assert response.status_code == status.HTTP_200_OK
            
            # diffprivlib_body["imputer_strategy"] = "median"
            # response = client.post(
            #     "/diffprivlib_query",
            #     json=diffprivlib_body,
            #     headers=self.headers,
            # )
            # assert response.status_code == status.HTTP_200_OK
            
            # diffprivlib_body["imputer_strategy"] = "most_frequent"
            # response = client.post(
            #     "/diffprivlib_query",
            #     json=diffprivlib_body,
            #     headers=self.headers,
            # )
            # assert response.status_code == status.HTTP_200_OK
            
            # Should not work unknow imputation strategy
            diffprivlib_body["imputer_strategy"] = "i_do_not_exist"
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "Imputation strategy i_do_not_exist not supported."
            }
            
            # Should not work: Privacy Leak Warning
            warnings.simplefilter("error", PrivacyLeakWarning)
            warnings.simplefilter("error", DiffprivlibCompatibilityWarning)
            diffprivlib_body = dict(example_diffprivlib)
            dpl_pipeline = Pipeline([
                ('scaler', models.StandardScaler(epsilon = 0.5)),
                ('classifier', models.LogisticRegression(epsilon = 1.0))
            ])
            dpl_string = serialise_pipeline(dpl_pipeline)
            diffprivlib_body['diffprivlib_json'] = dpl_string
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            LOG.error(response)
            response_dict = json.loads(response.content.decode("utf8"))
            LOG.error(response_dict)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "PrivacyLeakWarning: "
                + "Bounds parameter hasn't been specified, so falling back to "
                + "determining bounds from the data.\n "
                + "This will result in additional privacy leakage.  "
                + "To ensure differential privacy with no additional privacy "
                + "loss, specify `bounds` for each valued returned by "
                + "np.mean().. "
                + "Lomas server cannot fit pipeline on data, "
                + "PrivacyLeakWarning is a blocker.",
                "library": "diffprivlib",
            }

    # def test_dummy_diffprivlib_query(self) -> None:
    #     """test_dummy_diffprivlib_query"""
    #     with TestClient(app) as client:
    #         # Expect to work
    #         response = client.post(
    #             "/dummy_diffprivlib_query", json=example_dummy_diffprivlib
    #         )
    #         assert response.status_code == status.HTTP_200_OK

    #         response_dict = json.loads(response.content.decode("utf8"))
    #         assert response_dict["query_response"]["columns"] == ["res_0"]
    #         assert response_dict["query_response"]["data"][0][0] > 0
    #         assert response_dict["query_response"]["data"][0][0] < 200

    # def test_diffprivlib_cost(self) -> None:
    #     """test_diffprivlib_cost"""
    #     with TestClient(app) as client:
    #         # Expect to work
    #         response = client.post(
    #             "/estimate_diffprivlib_cost", json=example_diffprivlib
    #         )
    #         assert response.status_code == status.HTTP_200_OK

    #         response_dict = json.loads(response.content.decode("utf8"))
    #         assert response_dict["epsilon_cost"] == SMARTNOISE_QUERY_EPSILON
    #         assert response_dict["delta_cost"] > SMARTNOISE_QUERY_DELTA
