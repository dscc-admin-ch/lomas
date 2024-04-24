from fastapi import status
from fastapi.testclient import TestClient
import json
from io import StringIO
import pandas as pd
import unittest

from app import app

from utils.example_inputs import (
    DUMMY_NB_ROWS,
    example_get_admin_db_data,
    example_get_dummy_dataset,
    example_smartnoise_sql,
    example_dummy_smartnoise_sql,
    example_smartnoise_sql_cost,
    example_opendp,
    example_dummy_opendp,
    IRIS_DATASET,
)
from utils.loggr import LOG

class TestRootAPIEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        print("TestRootAPIEndpoint")
        self.user_name = "Dr. Antartica"
        self.dataset = "PENGUIN"
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "user_name": self.user_name,
        }

    # def test_state(self):
    #     with TestClient(app) as client:
    #         response = client.get("/state", headers=self.headers)
    #         assert response.status_code == status.HTTP_200_OK
            
    #         response = json.loads(response.content.decode("utf8"))
    #         
    #         LOG.error(self.headers)
    #         LOG.error(response)
    #         assert response == {
    #             "requested_by": self.user_name,
    #             "state": {
    #                 "state": ["Startup event", "Startup completed", "LIVE"],
    #                 "message": [
    #                     "Loading config",
    #                     "Loading admin database",
    #                     "Loading dataset store",
    #                     "Loading query handler",
    #                     "Startup completed",
    #                     "Server start condition OK"
    #                 ],
    #                 "LIVE": True,
    #             },
    #         }

    def test_get_dataset_metadata(self):
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/get_dataset_metadata",
                json=example_get_admin_db_data,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            metadata = json.loads(response.content.decode("utf8"))
            assert isinstance(metadata, dict), "metadata should be a dict"
            assert "max_ids" in metadata, "max_ids should be in metadata"
            assert "row_privacy" in metadata, "max_ids should be in metadata"

            # Expect to fail: dataset does not exist
            fake_dataset = "I_do_not_exist"
            response = client.post(
                "/get_dataset_metadata",
                json={"dataset_name": fake_dataset},
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": f"Dataset {fake_dataset} does not "
                + "exists. Please, verify the client object initialisation."
            }

    def test_get_dummy_dataset(self):
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/get_dummy_dataset", json=example_get_dummy_dataset
            )
            assert response.status_code == status.HTTP_200_OK

            data = response.content.decode("utf8")
            df = pd.read_csv(StringIO(data))
            assert isinstance(
                df, pd.DataFrame
            ), "Response should be a pd.DataFrame"
            assert (
                df.shape[0] == DUMMY_NB_ROWS
            ), "Dummy pd.DataFrame does not have expected number of rows"

            # Expect to fail: dataset does not exist
            fake_dataset = "I_do_not_exist"
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": fake_dataset,
                    "dummy_nb_rows": DUMMY_NB_ROWS,
                    "dummy_seed": 0,
                },
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": f"Dataset {fake_dataset} does not "
                + "exists. Please, verify the client object initialisation."
            }

            # Expect to fail: missing argument dummy_nb_rows
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": IRIS_DATASET,
                },
                headers=self.headers,
            )
            LOG.error(response.json())
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # def test_smartnoise_query(self):
    #     with TestClient(app) as client:
    #         # Expect to work
    #         response = client.post(
    #             "/smartnoise_query", json=example_smartnoise_sql
    #         )
    #         assert response.status_code == status.HTTP_200_OK

    #         response_dict = json.loads(response.content.decode("utf8"))
    #         assert response_dict == {
    #             "requested_by": self.user_name,
    #             "query_response": pd.DataFrame(),
    #             "spent_epsilon": 1.0,
    #             "spent_delta": 0.5,
    #         }

    # def test_dummy_smartnoise_query(self):
    #     with TestClient(app) as client:
    #         # Expect to work
    #         response = client.post(
    #             "/dummy_smartnoise_query", json=example_dummy_smartnoise_sql
    #         )
    #         assert response.status_code == status.HTTP_200_OK

    #         response_dict = json.loads(response.content.decode("utf8"))
    #         assert response_dict == {
    #             "query_response": pd.DataFrame(),
    #         }

    # def test_smartnoise_cost(self):
    #     with TestClient(app) as client:
    #         # Expect to work
    #         response = client.post(
    #             "/estimate_smartnoise_cost", json=example_smartnoise_sql_cost
    #         )
    #         assert response.status_code == status.HTTP_200_OK
    #         response_dict = json.loads(response.content.decode("utf8"))
    #         assert response_dict == {
    #             "epsilon_cost": 1.5,
    #             "delta_cost": 0.0,
    #         }
