import base64
import json
import pickle

from fastapi import status
from fastapi.testclient import TestClient
from smartnoise_synth_logger import serialise_constraints
from snsynth.transform import (
    ChainTransformer,
    LabelTransformer,
    MinMaxTransformer,
    OneHotEncoder,
)

from app import app
from constants import SSynthTableTransStyle
from tests.constants import PENGUIN_COLUMNS, PUMS_COLUMNS
from tests.test_api import TestRootAPIEndpoint
from utils.query_examples import (
    example_dummy_smartnoise_synth,
    example_smartnoise_synth,
)


def get_model(query_response):
    """Unpickle model from API response"""
    model = base64.b64decode(query_response)
    model = pickle.loads(model)
    return model


class TestDiffPrivLibEndpoint(TestRootAPIEndpoint):  # pylint: disable=R0904
    """
    Test Smartnoise Synth Endpoints with different models
    """

    def test_smartnoise_synth_query(self) -> None:
        """Test smartnoise synth query"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/smartnoise_synth_query",
                json=example_smartnoise_synth,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["spent_epsilon"] == 0.1
            assert response_dict["spent_delta"] == 1e-05

            model = get_model(response_dict["query_response"])
            assert model.__class__.__name__ == "DPCTGAN"

            df = model.sample(10)
            assert list(df.columns) == PENGUIN_COLUMNS
            assert model.epsilon == response_dict["spent_epsilon"]

    def test_smartnoise_synth_query_transformer_type(self) -> None:
        """Test smartnoise synth query transformer_type"""
        with TestClient(app, headers=self.headers) as client:

            body = dict(example_smartnoise_synth)
            body["table_transformer_style"] = SSynthTableTransStyle.CUBE

            # Expect to work
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            # TypeError: list indices must be integers or slices, not numpy.float32
            response_dict = json.loads(response.content.decode("utf8"))
            assert response.status_code == status.HTTP_200_OK

            _ = get_model(response_dict["query_response"])
            # df = model.sample(10)
            # assert list(df.columns) == PENGUIN_COLUMNS

    def test_smartnoise_synth_query_select_cols(self) -> None:
        """Test smartnoise synth query select_cols"""
        with TestClient(app, headers=self.headers) as client:

            # Expect to work
            body = dict(example_smartnoise_synth)
            body["select_cols"] = ["species", "island"]
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            model = get_model(response_dict["query_response"])
            df = model.sample(1)
            assert list(df.columns) == ["species", "island"]

            # Expect to fail
            body = dict(example_smartnoise_synth)
            body["select_cols"] = ["species", "idonotexist"]
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["InvalidQueryException"].startswith(
                "Error while selecting provided select_cols: "
            )

    def test_smartnoise_synth_query_constraints(self) -> None:
        """Test smartnoise synth query constraints"""
        with TestClient(app, headers=self.headers) as client:

            constraints = {
                "species": ChainTransformer(
                    [LabelTransformer(nullable=True), OneHotEncoder()]
                ),
                "island": ChainTransformer(
                    [LabelTransformer(nullable=True), OneHotEncoder()]
                ),
                "bill_length_mm": MinMaxTransformer(
                    lower=30.0, upper=65.0, nullable=True
                ),
                "bill_depth_mm": MinMaxTransformer(
                    lower=13.0, upper=23.0, nullable=True
                ),
                "flipper_length_mm": MinMaxTransformer(
                    lower=150.0, upper=250.0, nullable=True
                ),
                "body_mass_g": MinMaxTransformer(
                    lower=2000.0, upper=7000.0, nullable=True
                ),
                "sex": ChainTransformer(
                    [LabelTransformer(nullable=True), OneHotEncoder()]
                ),
            }

            body = dict(example_smartnoise_synth)
            body["constraints"] = serialise_constraints(constraints)

            # Expect to work
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            model = get_model(response_dict["query_response"])
            df = model.sample(1)
            assert list(df.columns) == PENGUIN_COLUMNS

    def test_smartnoise_synth_query_private_id(self) -> None:
        """Test smartnoise synth query on other dataset for private id
        and categorical int columns
        """
        with TestClient(app, headers=self.headers) as client:

            # Expect to work
            body = dict(example_smartnoise_synth)
            body["dataset_name"] = "PUMS"
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            model = get_model(response_dict["query_response"])
            df = model.sample(1)
            assert list(df.columns) == PUMS_COLUMNS

    def test_smartnoise_synth_query_delta_none(self) -> None:
        """Test smartnoise synth query on other synthesizer with delta None"""
        with TestClient(app, headers=self.headers) as client:

            # Expect to work
            body = dict(example_dummy_smartnoise_synth)
            body["dataset_name"] = "PUMS"
            body["delta"] = None
            body["synth_params"] = {"batch_size": 2, "epochs": 5}
            response = client.post(
                "/dummy_smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            model = get_model(response_dict["query_response"])
            df = model.sample(1)
            assert list(df.columns) == PUMS_COLUMNS

    def test_dummy_smartnoise_synth_query(self) -> None:
        """test_dummy_smartnoise_synth_query"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_smartnoise_synth_query",
                json=example_dummy_smartnoise_synth,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            model = base64.b64decode(response_dict["query_response"])
            model = pickle.loads(model)
            assert model.__class__.__name__ == "DPCTGAN"

            # Expect to fail: user does have access to dataset
            body = dict(example_dummy_smartnoise_synth)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_smartnoise_synth_cost(self) -> None:
        """test_smartnoise_synth_cost"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_smartnoise_synth_cost",
                json=example_smartnoise_synth,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] == 0.1
            assert response_dict["delta_cost"] == 1e-5

            # Expect to fail: user does have access to dataset
            body = dict(example_smartnoise_synth)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_smartnoise_synth_cost",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }
