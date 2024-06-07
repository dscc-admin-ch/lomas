import json
import os
import unittest
from io import StringIO

import pandas as pd
from fastapi import status
from fastapi.testclient import TestClient
from pymongo.database import Database

from admin_database.utils import get_mongodb
from mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)
from app import app
from constants import EPSILON_LIMIT, DPLibraries
from tests.constants import ENV_MONGO_INTEGRATION
from utils.config import CONFIG_LOADER
from utils.example_inputs import (
    DUMMY_NB_ROWS,
    PENGUIN_DATASET,
    SMARTNOISE_QUERY_DELTA,
    SMARTNOISE_QUERY_EPSILON,
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_get_admin_db_data,
    example_get_dummy_dataset,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005


class TestRootAPIEndpoint(unittest.TestCase):
    """
    End-to-end tests of the api endpoints.

    This test can be both executed as an integration test
    (enabled by setting LOMAS_TEST_MONGO_INTEGRATION to True),
    or a standard test. The first requires a mongodb to be started
    before running while the latter will use a local YamlDatabase.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Read correct config depending on the database we test against
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in ("true", "1", "t"):
            CONFIG_LOADER.load_config(
                config_path="tests/test_configs/test_config_mongo.yaml",
                secrets_path="tests/test_configs/test_secrets.yaml",
            )
        else:
            CONFIG_LOADER.load_config(
                config_path="tests/test_configs/test_config.yaml",
                secrets_path="tests/test_configs/test_secrets.yaml",
            )

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self) -> None:
        """_summary_"""
        self.user_name = "Dr. Antartica"
        self.dataset = PENGUIN_DATASET
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["user-name"] = self.user_name

        # Fill up database if needed
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in ("true", "1", "t"):
            self.db: Database = get_mongodb()

            add_users_via_yaml(
                self.db,
                yaml_file="tests/test_data/test_user_collection.yaml",
                clean=True,
                overwrite=True,
            )
            add_datasets_via_yaml(
                self.db,
                yaml_file="tests/test_data/test_datasets.yaml",
                clean=True,
                overwrite_datasets=True,
                overwrite_metadata=True,
            )

    def tearDown(self) -> None:
        # Clean up database if needed
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in ("true", "1", "t"):
            drop_collection(self.db, "metadata")
            drop_collection(self.db, "datasets")
            drop_collection(self.db, "users")
            drop_collection(self.db, "queries_archives")

    def test_state(self) -> None:
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            response = client.get("/state", headers=self.headers)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["state"]["LIVE"]

    def test_get_dataset_metadata(self) -> None:
        """_summary_"""
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
            assert "columns" in metadata, "columns should be in metadata"

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
        """_summary_"""
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
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_smartnoise_query(self) -> None:
        """Test smartnoise-sql query"""
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
            assert response_dict["spent_epsilon"] == SMARTNOISE_QUERY_EPSILON
            assert response_dict["spent_delta"] >= SMARTNOISE_QUERY_DELTA

            # Expect to fail: missing parameters: delta and mechanisms
            response = client.post(
                "/smartnoise_query",
                json={
                    "query_str": "SELECT COUNT(*) AS NB_ROW FROM df",
                    "dataset_name": PENGUIN_DATASET,
                    "epsilon": SMARTNOISE_QUERY_EPSILON,
                    "postprocess": True,
                },
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            response_dict = json.loads(response.content.decode("utf8"))[
                "detail"
            ]
            assert response_dict[0]["type"] == "missing"
            assert response_dict[0]["loc"] == ["body", "delta"]
            assert response_dict[1]["type"] == "missing"
            assert response_dict[1]["loc"] == ["body", "mechanisms"]

            # Expect to fail: query does not make sense
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise[
                "query_str"
            ] = "SELECT AVG(bill) FROM df"  # no 'bill' column
            response = client.post(
                "/smartnoise_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "Error obtaining cost: "
                + "Column cannot be found bill",
                "library": "smartnoise_sql",
            }

            # Expect to fail: dataset without access
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["dataset_name"] = "IRIS"
            response = client.post(
                "/smartnoise_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + "Dr. Antartica does not have access to IRIS."
            }

            # Expect to fail: dataset does not exist
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["dataset_name"] = "I_do_not_exist"
            response = client.post(
                "/smartnoise_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "Dataset I_do_not_exist does not exists. "
                + "Please, verify the client object initialisation."
            }

            # Expect to fail: user does not exist
            new_headers = self.headers
            new_headers["user-name"] = "I_do_not_exist"
            response = client.post(
                "/smartnoise_query",
                json=example_smartnoise_sql,
                headers=new_headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + "User I_do_not_exist does not exist. "
                + "Please, verify the client object initialisation."
            }

    def test_dummy_smartnoise_query(self) -> None:
        """_summary_"""
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
        """_summary_"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_smartnoise_cost", json=example_smartnoise_sql_cost
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] == SMARTNOISE_QUERY_EPSILON
            assert response_dict["delta_cost"] > SMARTNOISE_QUERY_DELTA

    def test_opendp_query(self) -> None:
        """_summary_"""
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
            trans = '{"version": "0.8.0", "ast": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "constructor", "func": "make_chain_tt", "module": "combinators", "args": [{"_type": "constructor", "func": "make_select_column", "module": "transformations", "kwargs": {"key": "bill_length_mm", "TOA": "String"}}, {"_type": "constructor", "func": "make_split_dataframe", "module": "transformations", "kwargs": {"separator": ",", "col_names": {"_type": "list", "_items": ["species", "island", "bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g", "sex"]}}}]}, "rhs": {"_type": "constructor", "func": "then_cast_default", "module": "transformations", "kwargs": {"TOA": "f64"}}}, "rhs": {"_type": "constructor", "func": "then_clamp", "module": "transformations", "kwargs": {"bounds": [30.0, 65.0]}}}, "rhs": {"_type": "constructor", "func": "then_resize", "module": "transformations", "kwargs": {"size": 346, "constant": 43.61}}}, "rhs": {"_type": "constructor", "func": "then_variance", "module": "transformations"}}}'  # noqa: E501 # pylint: disable=C0301
            response = client.post(
                "/opendp_query",
                json={
                    "dataset_name": PENGUIN_DATASET,
                    "opendp_json": trans,
                },
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": "The pipeline provided is not a "
                + "measurement. It cannot be processed in this server."
            }

    def test_dummy_opendp_query(self) -> None:
        """_summary_"""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_opendp_query", json=example_dummy_opendp
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"] > 0

    def test_opendp_cost(self) -> None:
        """_summary_"""
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
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_initial_budget", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["initial_epsilon"] == INITAL_EPSILON
            assert response_dict["initial_delta"] == INITIAL_DELTA

            # Query to spend budget
            _ = client.post(
                "/smartnoise_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )

            # Response should stay the same
            response_2 = client.post(
                "/get_initial_budget", json=example_get_admin_db_data
            )
            assert response_2.status_code == status.HTTP_200_OK
            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert response_dict_2 == response_dict

    def test_get_total_spent_budget(self) -> None:
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_total_spent_budget", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["total_spent_epsilon"] == 0
            assert response_dict["total_spent_delta"] == 0

            # Query to spend budget
            _ = client.post(
                "/smartnoise_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )

            # Response should have updated spent budget
            response_2 = client.post(
                "/get_total_spent_budget", json=example_get_admin_db_data
            )
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert response_dict_2 != response_dict
            assert (
                response_dict_2["total_spent_epsilon"]
                == SMARTNOISE_QUERY_EPSILON
            )
            assert (
                response_dict_2["total_spent_delta"] >= SMARTNOISE_QUERY_DELTA
            )

    def test_get_remaining_budget(self) -> None:
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_remaining_budget", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["remaining_epsilon"] == INITAL_EPSILON
            assert response_dict["remaining_delta"] == INITIAL_DELTA

            # Query to spend budget
            _ = client.post(
                "/smartnoise_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )

            # Response should have removed spent budget
            response_2 = client.post(
                "/get_remaining_budget", json=example_get_admin_db_data
            )
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert response_dict_2 != response_dict
            assert (
                response_dict_2["remaining_epsilon"]
                == INITAL_EPSILON - SMARTNOISE_QUERY_EPSILON
            )
            assert (
                response_dict_2["remaining_delta"]
                <= INITIAL_DELTA - SMARTNOISE_QUERY_DELTA
            )

    def test_get_previous_queries(self) -> None:
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_previous_queries", json=example_get_admin_db_data
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["previous_queries"] == []

            # Query to archive 1 (smartnoise)
            query_res = client.post(
                "/smartnoise_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )
            query_res = json.loads(query_res.content.decode("utf8"))

            # Response should have one element in list
            response_2 = client.post(
                "/get_previous_queries", json=example_get_admin_db_data
            )
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert len(response_dict_2["previous_queries"]) == 1
            assert (
                response_dict_2["previous_queries"][0]["dp_librairy"]
                == DPLibraries.SMARTNOISE_SQL
            )
            assert (
                response_dict_2["previous_queries"][0]["client_input"]
                == example_smartnoise_sql
            )
            assert (
                response_dict_2["previous_queries"][0]["response"] == query_res
            )

            # Query to archive 2 (opendp)
            query_res = client.post(
                "/opendp_query",
                json=example_opendp,
            )
            query_res = json.loads(query_res.content.decode("utf8"))

            # Response should have two elements in list
            response_3 = client.post(
                "/get_previous_queries", json=example_get_admin_db_data
            )
            assert response_3.status_code == status.HTTP_200_OK

            response_dict_3 = json.loads(response_3.content.decode("utf8"))
            assert len(response_dict_3["previous_queries"]) == 2
            assert (
                response_dict_3["previous_queries"][0]
                == response_dict_2["previous_queries"][0]
            )
            assert (
                response_dict_3["previous_queries"][1]["dp_librairy"]
                == DPLibraries.OPENDP
            )
            assert (
                response_dict_3["previous_queries"][1]["client_input"]
                == example_opendp
            )
            assert (
                response_dict_3["previous_queries"][1]["response"] == query_res
            )

    def test_budget_over_limit(self) -> None:
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            # Should fail: too much budget on one go
            smartnoise_body = dict(example_smartnoise_sql)
            smartnoise_body["epsilon"] = EPSILON_LIMIT * 2

            response = client.post(
                "/smartnoise_query",
                json=smartnoise_body,
                headers=self.headers,
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            error = response.json()["detail"][0]
            assert error["type"] == "less_than_equal"
            assert error["loc"] == ["body", "epsilon"]
            assert error["msg"] == "Input should be less than or equal to 5"

    def test_subsequent_budget_limit_logic(self) -> None:
        """_summary_"""
        with TestClient(app, headers=self.headers) as client:
            # Should fail: too much budget after three queries
            smartnoise_body = dict(example_smartnoise_sql)
            smartnoise_body["epsilon"] = 4.0

            # spend 4.0 (total_spent = 4.0 <= INTIAL_BUDGET = 10.0)
            response = client.post(
                "/smartnoise_query",
                json=smartnoise_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name

            # spend 2*4.0 (total_spent = 8.0 <= INTIAL_BUDGET = 10.0)
            response = client.post(
                "/smartnoise_query",
                json=smartnoise_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name

            # spend 3*4.0 (total_spent = 12.0 > INTIAL_BUDGET = 10.0)
            response = client.post(
                "/smartnoise_query",
                json=smartnoise_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": "Not enough budget for this query "
                + "epsilon remaining 2.0, "
                + "delta remaining 0.004970000100000034."
            }
