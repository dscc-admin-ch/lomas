import json

from fastapi import status
from fastapi.testclient import TestClient

from app import app
from tests.test_api_root import TestSetupRootAPIEndpoint
import polars as pl
import io
import opendp.prelude as dp
from utils.example_inputs import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    example_opendp_polars,
    OPENDP_POLARS_JSON
)


def get_lf_from_json() -> pl.LazyFrame:
    lf = pl.LazyFrame.deserialize(
        io.StringIO(OPENDP_POLARS_JSON), format="json")

    return lf

def mean_query_serialized(lf):
    plan = lf.select(
        pl.col("income").dp.mean(bounds=(1000, 100000), scale=1000.0)
    )
    
    return plan.serialize(format="json")

def group_query_serialized(lf):
    plan = lf.group_by("sex").agg([
        pl.col("income").dp.mean(bounds=(1000, 100000), scale=100.0)
    ]).sort("income")
    
    return plan.serialize(format="json")

def multiple_group_query_serialized(lf):
    plan = lf.group_by(["sex","region"]).agg([
        pl.col("income").dp.mean(bounds=(1000, 100000), scale=100.0)
    ]).sort("income")
    
    return plan.serialize(format="json")
    
class TestOpenDpPolarsEndpoint(
    TestSetupRootAPIEndpoint
):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint with different polars plans.
    """

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:
            lf = get_lf_from_json()
            json_plan = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan
            
            
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
            lf = get_lf_from_json()
            json_plan = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan
            
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
            lf = get_lf_from_json()
            json_plan = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan
            
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
    
    def test_grouping_query(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            
            lf = get_lf_from_json()
            json_plan = group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan
            example_opendp_polars["by_config"] = ["sex"]
            
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            lf = get_lf_from_json()
            json_plan = multiple_group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan
            example_opendp_polars["by_config"] = ["sex","region"]
            
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            
            # Expect to fail if by_config not specified by user
            example_opendp_polars["by_config"] = None
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            
            # Expect to fail, wrong column selected
            example_opendp_polars["by_config"] = ["region"]
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
