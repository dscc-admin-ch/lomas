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

from app import app
from constants import DPLibraries
from tests.test_api import TestRootAPIEndpoint
from utils.logger import LOG
from utils.query_examples import example_diffprivlib, example_dummy_diffprivlib


def validate_pipeline(response):
    """Validate that the pipeline ran successfully
    Returns a model and a score.
    """
    assert response.status_code == status.HTTP_200_OK
    response_dict = json.loads(response.content.decode("utf8"))

    if not response_dict["query_response"]["score"]:
        LOG.error(" ************** DIFFPRIVLIB ERROR ************** ")
        # Temporary LOGs to help understand why tests sometimes fail
        LOG.error(response_dict)
        LOG.error(response_dict["query_response"])
        LOG.error(response_dict["query_response"]["score"])

    assert response_dict["query_response"]["score"]
    assert response_dict["query_response"]["model"]


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

            response = test_imputation(example_diffprivlib, "mean")
            response_dict = json.loads(response.content.decode("utf8"))
            assert response.status_code == status.HTTP_200_OK

            response = test_imputation(example_diffprivlib, "median")
            assert response.status_code == status.HTTP_200_OK

            response = test_imputation(example_diffprivlib, "most_frequent")
            assert response.status_code == status.HTTP_200_OK

            # Should not work unknow imputation strategy
            response = test_imputation(example_diffprivlib, "i_do_not_exist")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "Imputation strategy i_do_not_exist not supported."
            }

            # Should not work: Privacy Leak Warning
            warnings.simplefilter("error", PrivacyLeakWarning)
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

            # Should not work: Compatibility Warning
            warnings.simplefilter("error", DiffprivlibCompatibilityWarning)
            with self.assertRaises(DiffprivlibCompatibilityWarning):
                Pipeline(
                    [
                        ("scaler", models.StandardScaler(epsilon=0.5)),
                        (
                            "classifier",
                            models.LogisticRegression(
                                epsilon=1.0, svd_solver="full"
                            ),
                        ),
                    ]
                )

    def test_logistic_regression_models(self) -> None:
        """Test diffprivlib query: Logistic Regression"""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])

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
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

    def test_linear_regression_models(self) -> None:
        """Test diffprivlib query: Linear Regression"""
        with TestClient(app, headers=self.headers) as client:
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
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            diffprivlib_body["feature_columns"] = ["bill_length_mm"]
            diffprivlib_body["target_columns"] = ["bill_length_mm"]
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

    def test_naives_bayes_model(self) -> None:
        """Test diffprivlib query: Gaussian Naives Bayes"""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])
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
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

    def test_trees_models(self) -> None:
        """Test diffprivlib query: Random Forest, Decision Tree"""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])

            # Test Random Forest
            pipeline = Pipeline(
                [
                    (
                        "rf",
                        models.RandomForestClassifier(
                            n_estimators=10,
                            epsilon=2.0,
                            bounds=bounds,
                            classes=["Adelie", "Chinstrap", "Gentoo"],
                        ),
                    ),
                ]
            )
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

            # Test Decision Tree Classifier
            pipeline = Pipeline(
                [
                    (
                        "dtc",
                        models.DecisionTreeClassifier(
                            epsilon=2.0,
                            bounds=bounds,
                            classes=["Adelie", "Chinstrap", "Gentoo"],
                        ),
                    ),
                ]
            )
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

    def test_clustering_models(self) -> None:
        """Test diffprivlib query: K-Means"""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])

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
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

            diffprivlib_body["target_columns"] = None
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

    def test_dimension_reduction_models(self) -> None:
        """Test diffprivlib query: PCA"""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])
            # Test PCA
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
            diffprivlib_body = dict(example_diffprivlib)
            diffprivlib_body["diffprivlib_json"] = serialise_pipeline(pipeline)
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(response)

    def test_dummy_diffprivlib_query(self) -> None:
        """test_dummy_diffprivlib_query"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_diffprivlib_query",
                json=example_dummy_diffprivlib,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"]["score"] > 0
            assert response_dict["query_response"]["model"]

            # Expect to fail: user does have access to dataset
            body = dict(example_dummy_diffprivlib)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_diffprivlib_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_diffprivlib_cost(self) -> None:
        """test_diffprivlib_cost"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_diffprivlib_cost",
                json=example_diffprivlib,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] == 1.5
            assert response_dict["delta_cost"] == 0

            # Expect to fail: user does have access to dataset
            body = dict(example_diffprivlib)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_diffprivlib_cost",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }
