import json
import warnings

from fastapi import status
from fastapi.testclient import TestClient
from io import StringIO
import pandas as pd
import polars as pl

from app import app
from tests.test_api import TestRootAPIEndpoint
from utils.example_inputs import DUMMY_NB_ROWS, DUMMY_SEED, dtypes_income_dataset, example_opendp_polars, FSO_INCOME_DATASET

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
    
    def get_body_json(self, client, column = "income", lb = 1000.0, ub = 100000.0, scale = 1000):
        
            
        # test income 
        res = client.post(
            "/get_dummy_dataset",
            json={
                "dataset_name": "FSO_INCOME_SYNTHETIC",
                "dummy_nb_rows": 1,
                "dummy_seed": 0,
            },
        )
        
        data = res.content.decode("utf8")
        df = pd.read_csv(StringIO(data), dtype=dtypes_income_dataset)
        lf = pl.from_pandas(df).lazy()
        plan = lf.select(
            pl.col(column).dp.mean(bounds=(lb, ub), scale=scale)
        )
        polars_string = plan.serialize()
        
        opendp_polars_body = dict(example_opendp_polars)
        opendp_polars_body["opendp_json"] = polars_string
        
        return opendp_polars_body
    
    def get_body_sum_json(self, client, column = "age", lb = 1, ub = 100, scale=1):
        
            
        # test income 
        res = client.post(
            "/get_dummy_dataset",
            json={
                "dataset_name": "FSO_INCOME_SYNTHETIC",
                "dummy_nb_rows": 1,
                "dummy_seed": 0,
            },
        )
        
        data = res.content.decode("utf8")
        df = pd.read_csv(StringIO(data), dtype=dtypes_income_dataset)
        lf = pl.from_pandas(df).lazy()
        plan = lf.select(
            pl.col(column).dp.sum(bounds=(lb, ub), scale=scale)
        )
        polars_string = plan.serialize()
        
        opendp_polars_body = dict(example_opendp_polars)
        opendp_polars_body["opendp_json"] = polars_string
        
        return opendp_polars_body
        

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:
            opendp_polars_body = self.get_body_json(client)
            
            # Laplace 
            response = client.post(
                "/opendp_query",
                json=opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            
            # Gaussian
            opendp_polars_body["mechanism"] = "Gaussian"
            response = client.post(
                "/opendp_query",
                json=opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            
            # TODO clean this
            # opendp_polars_body = self.get_body_json(client, column="age", lb=1, ub=100, scale=1)
            # # response = client.post(                "/opendp_query",                json=opendp_polars_body,            )
            # data = json.loads(opendp_polars_body["opendp_json"])
            # data['Projection']['schema']['inner']['age']="Int32"
            # opendp_polars_body["opendp_json"] = str(data)
            # opendp_polars_body["output_measure_type_arg"] = "int"
            # response = client.post(
            #     "/opendp_query",
            #     json=opendp_polars_body,
            # )
            
    def test_opendp_polars_cost(self) -> None:
        """test_opendp_polars_cost"""
        with TestClient(app, headers=self.headers) as client:
            opendp_polars_body = self.get_body_json(client)
            
            # Expect to work
            response = client.post(
                "/estimate_opendp_cost",
                json=opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] == 0

            # Check estimation works for Gaussian mechanism
            opendp_polars_body["mechanism"] = "Gaussian"
            response = client.post(
                "/estimate_opendp_cost",
                json=opendp_polars_body,
            )
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] > 0.0
            
            # Should fail: user does not have access to dataset
            opendp_polars_body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_opendp_cost",
                json=opendp_polars_body,
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }
            
    def test_dummy_opendp_polars_query(self) -> None:
        """test_dummy_opendp_polars_query"""
        with TestClient(app, headers=self.headers) as client:
            opendp_polars_body = self.get_body_json(client)
            
            # Expect to work
            opendp_polars_body["dummy_nb_rows"]=DUMMY_NB_ROWS
            opendp_polars_body["dummy_seed"]=DUMMY_SEED
            response = client.post(
                "/dummy_opendp_query",
                json=opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            
            assert response_dict["query_response"]
            
            opendp_polars_body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_opendp_query",
                json=opendp_polars_body,
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