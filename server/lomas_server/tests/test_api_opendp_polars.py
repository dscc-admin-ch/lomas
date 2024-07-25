import json
import warnings

from fastapi import status
from fastapi.testclient import TestClient

from app import app
from tests.test_api import TestRootAPIEndpoint
from utils.example_inputs import DUMMY_NB_ROWS, DUMMY_SEED

def validate_pipeline(response):
    """Validate that the pipeline ran successfully
    Returns a model and a score.
    """
    assert response.status_code == status.HTTP_200_OK
    response_dict = json.loads(response.content.decode("utf8"))
    assert response_dict["query_response"]["score"]
    assert response_dict["query_response"]["model"]


class TestOpenDpPolarsEndpoint(TestRootAPIEndpoint):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint with different polars plans

    TODO: Combination of the following
    - mechanisms: gaussian, laplace
    - measure type args: float64, int
    - dummy query, cost, query
    """

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:
            
            # Laplace 
            response = client.post(
                "/opendp_query",
                json=self.opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            
            # Gaussian
            self.opendp_polars_body["mechanism"] = "Gaussian"
            response = client.post(
                "/opendp_query",
                json=self.opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            
    def test_opendp_polars_cost(self) -> None:
        """test_opendp_polars_cost"""
        with TestClient(app, headers=self.headers) as client:
            
            # Expect to work
            response = client.post(
                "/estimate_opendp_cost",
                json=self.opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] == 0

            # Check estimation works for Gaussian mechanism
            self.opendp_polars_body["mechanism"] = "Gaussian"
            response = client.post(
                "/estimate_opendp_cost",
                json=self.opendp_polars_body,
            )
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] > 0.0
            
            # Should fail: user does not have access to dataset
            self.opendp_polars_body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_opendp_cost",
                json=self.opendp_polars_body,
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }
            
    def test_dummy_opendp_polars_query(self) -> None:
        """test_dummy_opendp_polars_query"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            self.opendp_polars_body["dummy_nb_rows"]=DUMMY_NB_ROWS
            self.opendp_polars_body["dummy_seed"]=DUMMY_SEED
            response = client.post(
                "/dummy_opendp_query",
                json=self.opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            
            assert response_dict["query_response"]
            
            self.opendp_polars_body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_opendp_query",
                json=self.opendp_polars_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }
            
    # def test_measure_types(self) -> None:
    #     """test_measure_types"""
    #     with TestClient(app, headers=self.headers) as client:
            
    #         breakpoint()
    #         self.opendp_polars_body["output_measure_type_arg"] = "int"
    #         self.opendp_polars_body["mechanism"] = "Laplace"
    #         response = client.post(
    #             "/opendp_query",
    #             json=self.opendp_polars_body,
    #         )