import json
import warnings

from diffprivlib import models
from diffprivlib.utils import (
    DiffprivlibCompatibilityWarning,
    PrivacyLeakWarning,
)
from diffprivlib_logger import serialise_pipeline
from fastapi import status
from fastapi.testclient import TestClient
from sklearn.pipeline import Pipeline
from tests.test_api import TestRootAPIEndpoint

from app import app
from constants import DPLibraries
from utils.example_inputs import (
    example_diffprivlib,
    example_dummy_diffprivlib,
)
# from utils.loggr import LOG


class TestDiffPrivLibEndpoint(TestRootAPIEndpoint):  # pylint: disable=R0904
    """
    Test DiffPrivLib Endpoint with different models
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
            def test_imputation(diffprivlib_body, imputer_strategy):
                diffprivlib_body = dict(diffprivlib_body)
                diffprivlib_body["imputer_strategy"] = imputer_strategy
                response = client.post(
                    "/diffprivlib_query",
                    json=diffprivlib_body,
                    headers=self.headers,
                )
                return response

            # response = test_imputation(example_diffprivlib, "mean")
            # assert response.status_code == status.HTTP_200_OK

            # response = test_imputation(example_diffprivlib, "median")
            # assert response.status_code == status.HTTP_200_OK

            # response = test_imputation(example_diffprivlib, "most_frequent")
            # assert response.status_code == status.HTTP_200_OK

            # Should not work unknow imputation strategy
            response = test_imputation(example_diffprivlib, "i_do_not_exist")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "Imputation strategy i_do_not_exist not supported."
            }

            # Should not work: Privacy Leak Warning
            warnings.simplefilter("error", PrivacyLeakWarning)
            warnings.simplefilter("error", DiffprivlibCompatibilityWarning)
            diffprivlib_body = dict(example_diffprivlib)
            dpl_pipeline = Pipeline(
                [
                    ("scaler", models.StandardScaler(epsilon=0.5)),
                    ("classifier", models.LogisticRegression(epsilon=1.0)),
                ]
            )
            dpl_string = serialise_pipeline(dpl_pipeline)
            diffprivlib_body["diffprivlib_json"] = dpl_string
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
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
                "library": DPLibraries.DIFFPRIVLIB,
            }

    def test_diffprivlib_models(self) -> None:
        """Test diffprivlib query"""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])

            def test_pipeline(
                diffprivlib_body,
                pipeline,
                feature_columns=None,
                target_columns=None,
            ):
                diffprivlib_body = dict(diffprivlib_body)
                if feature_columns:
                    diffprivlib_body["feature_columns"] = feature_columns

                if target_columns:
                    diffprivlib_body["target_columns"] = target_columns

                diffprivlib_body["diffprivlib_json"] = serialise_pipeline(
                    pipeline
                )
                response = client.post(
                    "/diffprivlib_query",
                    json=diffprivlib_body,
                    headers=self.headers,
                )
                return response

            def validate_pipeline(response):
                assert response.status_code == status.HTTP_200_OK
                response_dict = json.loads(response.content.decode("utf8"))
                assert response_dict["query_response"]["score"]
                assert response_dict["query_response"]["model"]

            # Test Logistic Regression
            pipeline = Pipeline(
                [
                    (
                        "scaler",
                        models.StandardScaler(epsilon=0.5, bounds=bounds),
                    ),
                    (
                        "classifier",
                        models.LogisticRegression(
                            epsilon=1.0, data_norm=83.69
                        ),
                    ),
                ]
            )
            response = test_pipeline(example_diffprivlib, pipeline)
            validate_pipeline(response)

            # Test Gaussian Naives Bayes
            pipeline = Pipeline(
                [
                    (
                        "scaler",
                        models.StandardScaler(epsilon=0.5, bounds=bounds),
                    ),
                    (
                        "gaussian",
                        models.GaussianNB(
                            epsilon=1.0, bounds=bounds, priors=(0.3, 0.3, 0.4)
                        ),
                    ),
                ]
            )
            response = test_pipeline(example_diffprivlib, pipeline)
            validate_pipeline(response)

            # # Test Random Forest TODO: fix bug in diffprivlib ?
            # pipeline = Pipeline(
            #     [
            #         (
            #             "rf",
            #             models.RandomForestClassifier(
            #                 n_estimators=10,
            #                 epsilon=2.0,
            #                 bounds=bounds,
            #                 classes=["Adelie", "Chinstrap", "Gentoo"],
            #             ),
            #         ),
            #     ]
            # )
            # response = test_pipeline(example_diffprivlib, pipeline)
            # validate_pipeline(response)

            # # Test Decision Tree Classifier  TODO: fix bug in diffprivlib ?
            # pipeline = Pipeline(
            #     [
            #         (
            #             "dtc",
            #             models.DecisionTreeClassifier(
            #                 epsilon=2.0,
            #                 bounds=bounds,
            #                 classes=["Adelie", "Chinstrap", "Gentoo"],
            #             ),
            #         ),
            #     ]
            # )
            # response = test_pipeline(example_diffprivlib, pipeline)
            # validate_pipeline(response)

            # Test Linear Regression
            pipeline = Pipeline(
                [
                    (
                        "lr",
                        models.LinearRegression(
                            epsilon=2.0,
                            bounds_X=(30.0, 65.0),
                            bounds_y=(13.0, 23.0),
                        ),
                    ),
                ]
            )
            response = test_pipeline(
                example_diffprivlib,
                pipeline,
                feature_columns=["bill_length_mm"],
                target_columns=["bill_depth_mm"],
            )
            validate_pipeline(response)

            # Test K-MEANS
            pipeline = Pipeline(
                [
                    (
                        "kmeans",
                        models.KMeans(
                            n_clusters=8, epsilon=2.0, bounds=bounds
                        ),
                    ),
                ]
            )
            response = test_pipeline(
                example_diffprivlib, pipeline, target_columns=None
            )
            validate_pipeline(response)
            response = test_pipeline(example_diffprivlib, pipeline)
            validate_pipeline(response)

            # Test PCA: TODO: also debug why not working (new scikit-learn version?)
            pipeline = Pipeline(
                [
                    (
                        "pca",
                        models.PCA(
                            n_components=8,
                            epsilon=2.0,
                            bounds=bounds,
                            data_norm=100,
                        ),
                    ),
                ]
            )
            response = test_pipeline(
                example_diffprivlib, pipeline, target_columns=None
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "Cannot fit pipeline on data "
                + "because PCA._fit_full() takes 3 positional arguments "
                + "but 5 were given",
                "library": DPLibraries.DIFFPRIVLIB,
            }
            # validate_pipeline(response)
            # response = test_pipeline(example_diffprivlib, pipeline)
            # validate_pipeline(response)

    def test_dummy_diffprivlib_query(self) -> None:
        """test_dummy_diffprivlib_query"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_diffprivlib_query", json=example_dummy_diffprivlib
            )
            # response_dict = json.loads(response.content.decode("utf8"))
            # LOG.error(response_dict)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"]["score"] > 0
            assert response_dict["query_response"]["model"]

    def test_diffprivlib_cost(self) -> None:
        """test_diffprivlib_cost"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_diffprivlib_cost", json=example_diffprivlib
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] == 1.5
            assert response_dict["delta_cost"] == 0
