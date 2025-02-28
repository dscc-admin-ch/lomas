import warnings

import pytest
from diffprivlib import models
from diffprivlib.utils import (
    DiffprivlibCompatibilityWarning,
    PrivacyLeakWarning,
)
from diffprivlib_logger import serialise_pipeline
from fastapi import status
from fastapi.testclient import TestClient
from sklearn.pipeline import Pipeline

from lomas_core.constants import DPLibraries
from lomas_core.models.exceptions import (
    ExternalLibraryExceptionModel,
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)
from lomas_core.models.requests_examples import (
    example_diffprivlib,
    example_dummy_diffprivlib,
)
from lomas_core.models.responses import (
    CostResponse,
    DiffPrivLibQueryResult,
    QueryResponse,
)
from lomas_server.app import app
from lomas_server.tests.test_api_root import TestSetupRootAPIEndpoint
from lomas_server.tests.utils import submit_job_wait, wait_for_job


def validate_pipeline(client, response) -> QueryResponse:
    """Validate that the pipeline ran successfully.

    Returns a model and a score.
    """
    assert response.status_code == status.HTTP_202_ACCEPTED

    job_uid = response.json()["uid"]
    job = wait_for_job(client, f"/status/{job_uid}")

    r_model = QueryResponse.model_validate(job.result)
    assert isinstance(r_model.result, DiffPrivLibQueryResult)

    return r_model


class TestDiffPrivLibEndpoint(TestSetupRootAPIEndpoint):  # pylint: disable=R0904
    """Test DiffPrivLib Endpoint with different models."""

    @pytest.mark.long
    def test_diffprivlib_query(self) -> None:
        """Test diffprivlib query."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/diffprivlib_query",
                json=example_diffprivlib,
                headers=self.headers,
            )
            r_model = validate_pipeline(client, response)
            assert r_model.requested_by == self.user_name
            assert r_model.result.score >= 0
            assert r_model.epsilon > 0
            assert r_model.delta == 0

            # # Should work for different imputation strategy (but does not yet #255)
            def test_imputation(diffprivlib_body, imputer_strategy):
                diffprivlib_body = dict(diffprivlib_body)
                diffprivlib_body["imputer_strategy"] = imputer_strategy
                job = submit_job_wait(
                    client,
                    "/diffprivlib_query",
                    json=diffprivlib_body,
                    headers=self.headers,
                )
                assert response.status_code == status.HTTP_202_ACCEPTED
                return job

            job = test_imputation(example_diffprivlib, "mean")
            assert job.status == "complete"

            job = test_imputation(example_diffprivlib, "median")
            assert job.status == "complete"

            job = test_imputation(example_diffprivlib, "most_frequent")
            assert job.status == "complete"

            # Should not work unknow imputation strategy
            job = test_imputation(example_diffprivlib, "i_do_not_exist")
            assert job.status == "failed"
            assert job.status_code == status.HTTP_400_BAD_REQUEST
            assert job.error == InvalidQueryExceptionModel(
                message="Imputation strategy i_do_not_exist not supported."
            )

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
            job = submit_job_wait(
                client,
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            assert job.status == "failed"
            assert job.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert job.error == ExternalLibraryExceptionModel(
                message="PrivacyLeakWarning: "
                + "Bounds parameter hasn't been specified, so falling back to "
                + "determining bounds from the data.\n "
                + "This will result in additional privacy leakage.  "
                + "To ensure differential privacy with no additional privacy "
                + "loss, specify `bounds` for each valued returned by "
                + "np.mean().. "
                + "Lomas server cannot fit pipeline on data, "
                + "PrivacyLeakWarning is a blocker.",
                library=DPLibraries.DIFFPRIVLIB,
            )

            # Should not work: Compatibility Warning
            warnings.simplefilter("error", DiffprivlibCompatibilityWarning)
            with self.assertRaises(DiffprivlibCompatibilityWarning):
                Pipeline(
                    [
                        ("scaler", models.StandardScaler(epsilon=0.5)),
                        (
                            "classifier",
                            models.LogisticRegression(epsilon=1.0, svd_solver="full"),
                        ),
                    ]
                )

    def test_logistic_regression_models(self) -> None:
        """Test diffprivlib query: Logistic Regression."""
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
                        models.LogisticRegression(epsilon=1.0, data_norm=83.69),
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
            validate_pipeline(client, response)

    def test_linear_regression_models(self) -> None:
        """Test diffprivlib query: Linear Regression."""
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
            validate_pipeline(client, response)

    def test_naives_bayes_model(self) -> None:
        """Test diffprivlib query: Gaussian Naives Bayes."""
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
                        models.GaussianNB(epsilon=1.0, bounds=bounds, priors=(0.3, 0.3, 0.4)),
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
            validate_pipeline(client, response)

    def test_trees_models(self) -> None:
        """Test diffprivlib query: Random Forest, Decision Tree."""
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
            validate_pipeline(client, response)

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
            validate_pipeline(client, response)

    def test_clustering_models(self) -> None:
        """Test diffprivlib query: K-Means."""
        with TestClient(app, headers=self.headers) as client:
            bounds = ([30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0])

            # Test K-MEANS
            pipeline = Pipeline(
                [
                    (
                        "kmeans",
                        models.KMeans(n_clusters=8, epsilon=2.0, bounds=bounds),
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
            validate_pipeline(client, response)

            diffprivlib_body["target_columns"] = None
            response = client.post(
                "/diffprivlib_query",
                json=diffprivlib_body,
                headers=self.headers,
            )
            validate_pipeline(client, response)

    def test_dimension_reduction_models(self) -> None:
        """Test diffprivlib query: PCA."""
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
            validate_pipeline(client, response)

    def test_dummy_diffprivlib_query(self) -> None:
        """Test_dummy_diffprivlib_query."""
        with TestClient(app) as client:
            # Expect to work
            job = submit_job_wait(
                client,
                "/dummy_diffprivlib_query",
                json=example_dummy_diffprivlib,
                headers=self.headers,
            )
            assert job is not None
            r_model = QueryResponse.model_validate(job.result)
            assert isinstance(r_model.result, DiffPrivLibQueryResult)
            assert r_model.result.score > 0

            # Expect to fail: user does have access to dataset
            body = dict(example_dummy_diffprivlib)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_diffprivlib_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to IRIS."
                ).model_dump()
            )

    def test_diffprivlib_cost(self) -> None:
        """Test_diffprivlib_cost."""
        with TestClient(app) as client:
            # Expect to work
            job = submit_job_wait(
                client,
                "/estimate_diffprivlib_cost",
                json=example_diffprivlib,
                headers=self.headers,
            )
            assert job is not None
            r_model = CostResponse.model_validate(job.result)
            assert r_model.epsilon == 1.5
            assert r_model.delta == 0

            # Expect to fail: user does have access to dataset
            body = dict(example_diffprivlib)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_diffprivlib_cost",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to IRIS."
                ).model_dump()
            )
