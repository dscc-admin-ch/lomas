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
    PENGUIN_DATASET,
)
from utils.loggr import LOG


class TestRootAPIEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        print("TestRootAPIEndpoint")
        self.user_name = "Dr. Antartica"
        self.dataset = PENGUIN_DATASET
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["user-name"] = self.user_name

    def test_state(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            response = client.get("/state", headers=self.headers)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["state"]["LIVE"]

    def test_get_dataset_metadata(self) -> None:
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

    def test_get_dummy_dataset(self) -> None:
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
                    "dataset_name": PENGUIN_DATASET,
                },
                headers=self.headers,
            )
            LOG.error(response.json())
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_smartnoise_query(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/smartnoise_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["query_response"]["columns"] == ["NB_ROW"]
            assert response_dict["query_response"]["data"][0][0] > 0
            assert response_dict["spent_epsilon"] == 0.1
            assert response_dict["spent_delta"] <= 1.5e-5

    def test_dummy_smartnoise_query(self) -> None:
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_smartnoise_query", json=example_dummy_smartnoise_sql
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"]["columns"] == ["res_0"]
            assert response_dict["query_response"]["data"][0][0] > 0
            assert response_dict["query_response"]["data"][0][0] < 200

    def test_smartnoise_cost(self) -> None:
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_smartnoise_cost", json=example_smartnoise_sql_cost
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            LOG.error(response_dict)
            assert response_dict["epsilon_cost"] == 0.1
            assert response_dict["delta_cost"] > 0
            assert response_dict["delta_cost"] > 0.00001

    def test_opendp_query(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/opendp_query",
                json=example_opendp,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["query_response"] > 0
            assert response_dict["spent_epsilon"] > 0.1
            assert response_dict["spent_delta"] == 0

            # Expect to fail: transormation instead of measurement
            trans_pipeline = '{"version": "0.8.0", "ast": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "constructor", "func": "make_chain_tt", "module": "combinators", "args": [{"_type": "constructor", "func": "make_select_column", "module": "transformations", "kwargs": {"key": "bill_length_mm", "TOA": "String"}}, {"_type": "constructor", "func": "make_split_dataframe", "module": "transformations", "kwargs": {"separator": ",", "col_names": {"_type": "list", "_items": ["species", "island", "bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g", "sex"]}}}]}, "rhs": {"_type": "constructor", "func": "then_cast_default", "module": "transformations", "kwargs": {"TOA": "f64"}}}, "rhs": {"_type": "constructor", "func": "then_clamp", "module": "transformations", "kwargs": {"bounds": [30.0, 65.0]}}}, "rhs": {"_type": "constructor", "func": "then_resize", "module": "transformations", "kwargs": {"size": 346, "constant": 43.61}}}, "rhs": {"_type": "constructor", "func": "then_variance", "module": "transformations"}}}'  # noqa: E501
            response = client.post(
                "/opendp_query",
                json={
                    "dataset_name": PENGUIN_DATASET,
                    "opendp_json": trans_pipeline,
                    "input_data_type": "df",
                },
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": "The pipeline provided is not a "
                + "measurement. It cannot be processed in this server."
            }

    def test_dummy_opendp_query(self) -> None:
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_opendp_query", json=example_dummy_opendp
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"] > 0

    def test_opendp_cost(self) -> None:
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_opendp_cost", json=example_opendp
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.1
            assert response_dict["delta_cost"] == 0

    def test_get_initial_budget(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_initial_budget", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["initial_epsilon"] == 10
            assert response_dict["initial_delta"] == 0.005

    def test_get_total_spent_budget(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_total_spent_budget", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["total_spent_epsilon"] == 0
            assert response_dict["total_spent_delta"] == 0

    def test_get_remaining_budget(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_remaining_budget", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["remaining_epsilon"] == 10
            assert response_dict["remaining_delta"] == 0.005

    def test_get_previous_queries(self) -> None:
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_previous_queries", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["previous_queries"] == []
