import json
import numpy as np
from fastapi import status
from fastapi.testclient import TestClient
from opendp.mod import enable_features

from lomas_server.tests.test_api_root import TestSetupRootAPIEndpoint
from lomas_core.constants import DPLibraries
from lomas_core.error_handler import InternalServerException
from lomas_core.models.config import DBConfig
from lomas_core.models.exceptions import (
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)
from lomas_core.models.requests_examples import (
    DUMMY_NB_ROWS,
    PENGUIN_DATASET,
    QUERY_DELTA,
    QUERY_EPSILON,
    example_get_admin_db_data,
    example_get_dummy_dataset,
    example_opendp,
    example_smartnoise_sql,
)
from lomas_core.models.responses import (
    DummyDsResponse,
    InitialBudgetResponse,
    QueryResponse,
    RemainingBudgetResponse,
    SpentBudgetResponse,
)
from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.app import app

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005

enable_features("floating-point")


class TestRootAPIEndpoint(TestSetupRootAPIEndpoint):  # pylint: disable=R0904
    """
    End-to-end tests of the api endpoints.

    This test can be both executed as an integration test
    (enabled by setting LOMAS_TEST_MONGO_INTEGRATION to True),
    or a standard test. The first requires a mongodb to be started
    before running while the latter will use a local YamlDatabase.
    """

    def test_config_and_internal_server_exception(self) -> None:
        """Test set wrong configuration."""

        # Put unknown admin database
        with self.assertRaises(InternalServerException) as context:
            admin_database_factory(DBConfig())
        self.assertEqual(str(context.exception), "Database type not supported.")

    def test_root(self) -> None:
        """Test root endpoint redirection to state endpoint."""
        with TestClient(app, headers=self.headers) as client:
            response_root = client.get("/", headers=self.headers)
            response_state = client.get("/state", headers=self.headers)
            assert response_root.status_code == response_state.status_code
            assert json.loads(response_root.content.decode("utf8")) == json.loads(
                response_state.content.decode("utf8")
            )

    def test_state(self) -> None:
        """Test state endpoint."""
        with TestClient(app, headers=self.headers) as client:
            response = client.get("/state", headers=self.headers)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["requested_by"] == self.user_name
            assert response_dict["state"]["LIVE"]

    def test_unknown_endpoint(self) -> None:
        """Test endpoint that does not exist."""
        with TestClient(app, headers=self.headers) as client:
            response = client.get("/idonotexist", headers=self.headers)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json() == {"detail": "Not Found"}

    def test_get_dataset_metadata(self) -> None:
        """Test_get_dataset_metadata."""
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
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message=f"Dataset {fake_dataset} does not "
                    + "exist. Please, verify the client object initialisation."
                ).model_dump()
            )

            # Expect to fail: user does have access to dataset
            other_dataset = "IRIS"
            response = client.post(
                "/get_dataset_metadata",
                json={"dataset_name": other_dataset},
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to {other_dataset}."
                ).model_dump()
            )

    def test_get_dummy_dataset(self) -> None:
        """Test_get_dummy_dataset."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/get_dummy_dataset",
                json=example_get_dummy_dataset,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            r_model = DummyDsResponse.model_validate(response_dict)

            assert (
                r_model.dummy_df.shape[0] == DUMMY_NB_ROWS
            ), "Dummy pd.DataFrame does not have expected number of rows"
            assert response_dict["datetime_columns"] == []

            expected_dtypes = [
                "string",
                "string",
                "float",
                "float",
                "float",
                "float",
                "string",
            ]
            assert (
                r_model.dummy_df.dtypes.values == expected_dtypes
            ).all(), f"Dtypes do not match: {r_model.dummy_df.dtypes} != {expected_dtypes}"

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
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message=f"Dataset {fake_dataset} does not "
                    + "exist. Please, verify the client object initialisation."
                ).model_dump()
            )

            # Expect to fail: missing argument dummy_nb_rows
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": PENGUIN_DATASET,
                },
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Expect to fail: user does have access to dataset
            other_dataset = "IRIS"
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": other_dataset,
                    "dummy_nb_rows": DUMMY_NB_ROWS,
                    "dummy_seed": 0,
                },
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to {other_dataset}."
                ).model_dump()
            )

            # Expect to fail: user does not exist
            fake_user = "fake_user"
            new_headers = self.headers
            new_headers["user-name"] = fake_user
            response = client.post(
                "/get_dummy_dataset",
                json=example_get_dummy_dataset,
                headers=new_headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"User {fake_user} does not "
                    + "exist. Please, verify the client object initialisation."
                ).model_dump()
            )

            # Expect to work with datetimes and another user
            fake_user = "BirthdayGirl"
            new_headers = self.headers
            new_headers["user-name"] = fake_user
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": "BIRTHDAYS",
                    "dummy_nb_rows": 10,
                    "dummy_seed": 0,
                },
                headers=new_headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            r_model = DummyDsResponse.model_validate(response_dict)

            assert r_model.dummy_df.shape[0] == 10, "Dummy pd.DataFrame does not have expected number of rows"

            expected_dtype = np.dtype("<M8[ns]")
            assert (
                r_model.dummy_df.dtypes.values[0] == expected_dtype
            ), f"Dtypes do not match: {r_model.dummy_df.dtypes} != {expected_dtype}"

    def test_get_initial_budget(self) -> None:
        """Test_get_initial_budget."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post("/get_initial_budget", json=example_get_admin_db_data)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = InitialBudgetResponse.model_validate(response_dict)
            assert response_model.initial_epsilon == INITAL_EPSILON
            assert response_model.initial_delta == INITIAL_DELTA

            # Query to spend budget
            _ = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )

            # Response should stay the same
            response_2 = client.post("/get_initial_budget", json=example_get_admin_db_data)
            assert response_2.status_code == status.HTTP_200_OK
            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert response_dict_2 == response_dict

    def test_get_total_spent_budget(self) -> None:
        """Test_get_total_spent_budget."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post("/get_total_spent_budget", json=example_get_admin_db_data)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = SpentBudgetResponse.model_validate(response_dict)
            assert response_model.total_spent_epsilon == 0
            assert response_model.total_spent_delta == 0

            # Query to spend budget
            _ = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )

            # Response should have updated spent budget
            response_2 = client.post("/get_total_spent_budget", json=example_get_admin_db_data)
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            response_model_2 = SpentBudgetResponse.model_validate(response_dict_2)

            assert response_dict_2 != response_dict
            assert response_model_2.total_spent_epsilon == QUERY_EPSILON
            assert response_model_2.total_spent_delta >= QUERY_DELTA

    def test_get_remaining_budget(self) -> None:
        """Test_get_remaining_budget."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post("/get_remaining_budget", json=example_get_admin_db_data)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = RemainingBudgetResponse.model_validate(response_dict)

            assert response_model.remaining_epsilon == INITAL_EPSILON
            assert response_model.remaining_delta == INITIAL_DELTA

            # Query to spend budget
            _ = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )

            # Response should have removed spent budget
            response_2 = client.post("/get_remaining_budget", json=example_get_admin_db_data)
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            response_model_2 = RemainingBudgetResponse.model_validate(response_dict_2)
            assert response_dict_2 != response_dict
            assert response_model_2.remaining_epsilon == INITAL_EPSILON - QUERY_EPSILON
            assert response_model_2.remaining_delta <= INITIAL_DELTA - QUERY_DELTA

    def test_get_previous_queries(self) -> None:
        """Test_get_previous_queries."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post("/get_previous_queries", json=example_get_admin_db_data)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["previous_queries"] == []

            # Query to archive 1 (smartnoise)
            query_res = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )
            query_res = json.loads(query_res.content.decode("utf8"))

            # Response should have one element in list
            response_2 = client.post("/get_previous_queries", json=example_get_admin_db_data)
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert len(response_dict_2["previous_queries"]) == 1
            assert response_dict_2["previous_queries"][0]["dp_library"] == DPLibraries.SMARTNOISE_SQL
            assert response_dict_2["previous_queries"][0]["client_input"] == example_smartnoise_sql
            assert response_dict_2["previous_queries"][0]["response"] == query_res

            # Query to archive 2 (opendp)
            query_res = client.post(
                "/opendp_query",
                json=example_opendp,
            )
            query_res = json.loads(query_res.content.decode("utf8"))

            # Response should have two elements in list
            response_3 = client.post("/get_previous_queries", json=example_get_admin_db_data)
            assert response_3.status_code == status.HTTP_200_OK

            response_dict_3 = json.loads(response_3.content.decode("utf8"))
            assert len(response_dict_3["previous_queries"]) == 2
            assert response_dict_3["previous_queries"][0] == response_dict_2["previous_queries"][0]
            assert response_dict_3["previous_queries"][1]["dp_library"] == DPLibraries.OPENDP
            assert response_dict_3["previous_queries"][1]["client_input"] == example_opendp
            assert response_dict_3["previous_queries"][1]["response"] == query_res

    def test_subsequent_budget_limit_logic(self) -> None:
        """Test_subsequent_budget_limit_logic."""
        with TestClient(app, headers=self.headers) as client:
            # Should fail: too much budget after three queries
            smartnoise_body = dict(example_smartnoise_sql)
            smartnoise_body["epsilon"] = 4.0

            # spend 4.0 (total_spent = 4.0 <= INTIAL_BUDGET = 10.0)
            response = client.post(
                "/smartnoise_sql_query",
                json=smartnoise_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            response_model = QueryResponse.model_validate(response_dict)
            assert response_model.requested_by == self.user_name

            # spend 2*4.0 (total_spent = 8.0 <= INTIAL_BUDGET = 10.0)
            response = client.post(
                "/smartnoise_sql_query",
                json=smartnoise_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            response_model = QueryResponse.model_validate(response_dict)
            assert response_model.requested_by == self.user_name

            # spend 3*4.0 (total_spent = 12.0 > INITIAL_BUDGET = 10.0)
            response = client.post(
                "/smartnoise_sql_query",
                json=smartnoise_body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message="Not enough budget for this query "
                    + "epsilon remaining 2.0, "
                    + "delta remaining 0.004970000100000034."
                ).model_dump()
            )
