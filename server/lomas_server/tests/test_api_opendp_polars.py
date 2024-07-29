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


class TestOpenDpPolarsEndpoint(TestRootAPIEndpoint):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint with different polars plans
    """
    
    def get_body_json(self, client, column = "income", lb = 1000.0, ub = 100000.0, scale = 1000):
        
            
        # test income 
        res = client.post(
            "/get_dummy_dataset",
            json={
                "dataset_name": FSO_INCOME_DATASET,
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
        polars_string = plan.serialize(format="json")
        
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
            opendp_polars_body["mechanism"] = "gaussian"
            response = client.post(
                "/opendp_query",
                json=opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            
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
            opendp_polars_body["mechanism"] = "gaussian"
            response = client.post(
                "/estimate_opendp_cost",
                json=opendp_polars_body,
            )
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] > 0.0
            
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
            
            # Test dummy query with Gaussian mechanism
            opendp_polars_body["dummy_nb_rows"]=DUMMY_NB_ROWS
            opendp_polars_body["dummy_seed"]=DUMMY_SEED
            opendp_polars_body["mechanism"]="gaussian"
            response = client.post(
                "/dummy_opendp_query",
                json=opendp_polars_body,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"]
    