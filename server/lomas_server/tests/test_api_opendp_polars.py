import json

from fastapi import status
from fastapi.testclient import TestClient

from app import app
from tests.test_api_root import TestSetupRootAPIEndpoint
from utils.example_inputs import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    example_opendp_polars,
)


class TestOpenDpPolarsEndpoint(
    TestSetupRootAPIEndpoint
):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint with different polars plans.
    """

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:

            # Laplace
            response = client.post(
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK

            # Gaussian
            example_opendp_polars["mechanism"] = "gaussian"
            response = client.post(
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK

    def test_opendp_polars_cost(self) -> None:
        """test_opendp_polars_cost"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            example_opendp_polars["mechanism"] = "laplace"
            response = client.post(
                "/estimate_opendp_cost",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] == 0

            # Check estimation works for Gaussian mechanism
            example_opendp_polars["mechanism"] = "gaussian"
            response = client.post(
                "/estimate_opendp_cost",
                json=example_opendp_polars,
            )
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] > 0.0

    def test_dummy_opendp_polars_query(self) -> None:
        """test_dummy_opendp_polars_query"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            example_opendp_polars["mechanism"] = "laplace"
            example_opendp_polars["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars["dummy_seed"] = DUMMY_SEED
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))

            assert response_dict["query_response"]

            # Test dummy query with Gaussian mechanism
            example_opendp_polars["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars["dummy_seed"] = DUMMY_SEED
            example_opendp_polars["mechanism"] = "gaussian"
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"]
