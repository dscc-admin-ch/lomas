import os
import re
import socket
from pathlib import Path

import numpy as np
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from lomas_client.utils import raise_error
from lomas_core.exceptions import (
    DatasetNotFoundException,
    LomasAPIException,
    UnauthorizedAccessException,
    UserNotFoundException,
)
from lomas_core.models.constants import (
    DUMMY_NB_ROWS,
    JobStatus,
)
from lomas_core.models.exceptions import LomasAPIErrorModel
from lomas_core.models.requests_examples import (
    EXAMPLE_GET_ADMIN_DB_DATA,
    EXAMPLE_GET_DUMMY_DATASET,
    EXAMPLE_OPENDP_POLARS,
    EXAMPLE_OPENDP_POLARS_PLAN,
    EXAMPLE_SMARTNOISE_SQL,
    PENGUIN_DATASET,
    QUERY_DELTA,
    QUERY_EPSILON,
)
from lomas_core.models.responses import (
    Budget,
    DummyDsResponse,
    QueryResponse,
)
from lomas_server.app import get_user_app
from lomas_server.tests.test_api_root import (
    INITIAL_BUDGET,
    TestSetupRootAPIEndpoint,
)
from lomas_server.tests.utils import submit_job_wait


class TestRootAPIEndpoint(TestSetupRootAPIEndpoint):
    """End-to-end tests of the api endpoints."""

    def test_root(self) -> None:
        """Test root endpoint redirection to state endpoint."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            response_root = client.get("/")
            response_state = client.get("/state")
            assert response_root.status_code == response_state.status_code
            assert response_root.json() == response_state.json()

    @pytest.mark.skip(reason="notify socket scope is no longer in Client level")
    def test_notify(self) -> None:
        os.environ["NOTIFY_SOCKET"] = ""
        with TestClient(get_user_app(self.config), headers=self.headers):
            pass

        del os.environ["NOTIFY_SOCKET"]
        with TestClient(get_user_app(self.config), headers=self.headers):
            pass

        os.environ["NOTIFY_SOCKET"] = "invalidSocket"
        with pytest.raises(OSError):
            with TestClient(get_user_app(self.config), headers=self.headers):
                pass

        os.environ["NOTIFY_SOCKET"] = "/tmp/valid.sock"
        Path(os.environ["NOTIFY_SOCKET"]).unlink(missing_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC) as sock:
            sock.bind(os.environ["NOTIFY_SOCKET"])
            with TestClient(get_user_app(self.config), headers=self.headers):
                pass

        # cleanup
        del os.environ["NOTIFY_SOCKET"]

    def test_state(self) -> None:
        """Test state endpoint."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            response = client.get("/live")
            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {"status": "alive"}

    def test_unknown_endpoint(self) -> None:
        """Test endpoint that does not exist."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            response = client.get("/idonotexist", headers=self.headers)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json() == {"detail": "Not Found"}

    def test_get_dataset_metadata(self) -> None:
        """Test_get_dataset_metadata."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Expect to work
            response = client.post("/get_dataset_metadata", json=EXAMPLE_GET_ADMIN_DB_DATA)
            assert response.status_code == status.HTTP_200_OK

            metadata = response.json()
            assert isinstance(metadata, dict), "metadata should be a dict"
            assert "max_contributions" in metadata, "max_contributions should be in metadata"
            assert "columns" in metadata, "columns should be in metadata"

            # Expect to fail: dataset does not exist
            fake_dataset = "I_do_not_exist"
            response = client.post("/get_dataset_metadata", json={"dataset_name": fake_dataset})
            assert response.status_code == status.HTTP_404_NOT_FOUND

            match_string = str(DatasetNotFoundException(fake_dataset))
            with pytest.raises(LomasAPIException, match=re.escape(match_string)):
                raise_error(response)

            # Expect to fail: user does have access to dataset
            other_dataset = "IRIS"
            response = client.post("/get_dataset_metadata", json={"dataset_name": other_dataset})
            assert response.status_code == status.HTTP_403_FORBIDDEN
            match_string = str(
                UnauthorizedAccessException(f"{self.user_name} does not have access to {other_dataset}.")
            )
            with pytest.raises(LomasAPIException, match=re.escape(match_string)):
                raise_error(response)

    def test_get_dummy_dataset(self) -> None:
        """Test_get_dummy_dataset."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_dummy_dataset",
                json=EXAMPLE_GET_DUMMY_DATASET,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = response.json()
            r_model = DummyDsResponse.model_validate(response_dict)

            assert r_model.dummy_df.shape[0] == DUMMY_NB_ROWS, (
                "Dummy pd.DataFrame does not have expected number of rows"
            )

            expected_dtypes = [
                "string",
                "string",
                "float",
                "float",
                "float",
                "float",
                "string",
            ]
            assert (r_model.dummy_df.dtypes.values == expected_dtypes).all(), (
                f"Dtypes do not match: {r_model.dummy_df.dtypes} != {expected_dtypes}"
            )

            # Expect to fail: dataset does not exist
            fake_dataset = "I_do_not_exist"
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": fake_dataset,
                    "dummy_nb_rows": DUMMY_NB_ROWS,
                    "dummy_seed": 0,
                },
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND
            match_string = str(DatasetNotFoundException(fake_dataset))
            with pytest.raises(LomasAPIException, match=re.escape(match_string)):
                raise_error(response)

            # Expect to fail: missing argument dummy_nb_rows
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": PENGUIN_DATASET,
                },
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

            # Expect to fail: user does have access to dataset
            other_dataset = "IRIS"
            response = client.post(
                "/get_dummy_dataset",
                json={
                    "dataset_name": other_dataset,
                    "dummy_nb_rows": DUMMY_NB_ROWS,
                    "dummy_seed": 0,
                },
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            match_string = str(
                UnauthorizedAccessException(f"{self.user_name} does not have access to {other_dataset}.")
            )
            with pytest.raises(LomasAPIException, match=re.escape(match_string)):
                raise_error(response)

            # Expect to fail: user does not exist
            new_headers = {**self.headers, "Authorization": "Bearer fake_user"}
            response = client.post(
                "/get_dummy_dataset",
                json=EXAMPLE_GET_DUMMY_DATASET,
                headers=new_headers,
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND
            match_string = str(UserNotFoundException("fake_user"))
            with pytest.raises(LomasAPIException, match=re.escape(match_string)):
                raise_error(response)

            # Expect to work with datetimes and another user
            new_headers = {**self.headers, "Authorization": "Bearer BirthdayGirl"}
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
            r_model = DummyDsResponse.model_validate(response.json())

            assert r_model.dummy_df.shape[0] == 10, "Dummy pd.DataFrame does not have expected number of rows"

            expected_dtype = np.dtype("<M8[ns]")
            assert r_model.dummy_df.dtypes.values[0] == expected_dtype, (
                f"Dtypes do not match: {r_model.dummy_df.dtypes} != {expected_dtype}"
            )

    def test_get_initial_budget(self) -> None:
        """Test_get_initial_budget."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Expect to work
            response = client.post("/get_initial_budget", json=EXAMPLE_GET_ADMIN_DB_DATA)
            assert response.status_code == status.HTTP_200_OK

            response_model = Budget.model_validate(response.json())
            assert response_model == Budget(epsilon=50.0, delta=INITIAL_BUDGET.delta)

            # Query to spend budget
            submit_job_wait(client, "/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)

            # Response should stay the same
            response_2 = client.post("/get_initial_budget", json=EXAMPLE_GET_ADMIN_DB_DATA)
            assert response_2.status_code == status.HTTP_200_OK
            assert response_2.json() == response.json()

    def test_get_total_spent_budget(self) -> None:
        """Test_get_total_spent_budget."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_total_spent_budget", json={"dataset_name": EXAMPLE_OPENDP_POLARS["dataset_name"]}
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = response.json()
            response_model = Budget.model_validate(response_dict)
            assert response_model == Budget.zero()

            # Query to spend budget
            submit_job_wait(client, "/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)

            # Response should have updated spent budget
            response_2 = client.post(
                "/get_total_spent_budget", json={"dataset_name": EXAMPLE_OPENDP_POLARS["dataset_name"]}
            )
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = response_2.json()
            response_model_2 = Budget.model_validate(response_dict_2)

            assert response_dict_2 != response_dict
            assert response_model_2.epsilon == QUERY_EPSILON
            assert response_model_2.delta >= QUERY_DELTA

    def test_get_remaining_budget(self) -> None:
        """Test_get_remaining_budget."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_remaining_budget", json={"dataset_name": EXAMPLE_OPENDP_POLARS["dataset_name"]}
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = response.json()
            response_model = Budget.model_validate(response_dict)

            assert response_model == INITIAL_BUDGET

            # Query to spend budget
            submit_job_wait(client, "/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)

            # Response should have removed spent budget
            response_2 = client.post(
                "/get_remaining_budget", json={"dataset_name": EXAMPLE_OPENDP_POLARS["dataset_name"]}
            )
            assert response_2.status_code == status.HTTP_200_OK

            response_dict_2 = response_2.json()
            response_model_2 = Budget.model_validate(response_dict_2)
            assert response_model_2 == pytest.approx(
                INITIAL_BUDGET - Budget(epsilon=QUERY_EPSILON, delta=QUERY_DELTA)
            )

    def test_get_previous_queries(self) -> None:
        """Test_get_previous_queries."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_previous_queries", json={"dataset_name": EXAMPLE_OPENDP_POLARS["dataset_name"]}
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = response.json()
            assert response_dict == []

            # Query to archive 1 (smartnoise)
            # job_smnoise = submit_job_wait(client, "/smartnoise_sql_query", json=example_smartnoise_sql)
            # assert job_smnoise is not None
            # assert job_smnoise.result is not None

            # Response should have one element in list
            # response_2 = client.post("/get_previous_queries", json=example_get_admin_db_data)
            # assert response_2.status_code == status.HTTP_200_OK
            #
            # response_dict_2 = response_2.json()
            # assert response_dict_2["previous_queries"] != []
            # previous_query = response_dict_2["previous_queries"][0]
            # assert previous_query["dp_library"] == DPLibraries.SMARTNOISE_SQL
            # assert previous_query["client_input"] == example_smartnoise_sql
            # assert previous_query["response"] == job_smnoise.result.model_dump(mode="json")

            # Query to archive 2 (opendp)
            job_opendp = submit_job_wait(client, "/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)
            assert job_opendp is not None
            assert job_opendp.result is not None

            # Response should have two elements in list
            response_3 = client.post(
                "/get_previous_queries", json={"dataset_name": EXAMPLE_OPENDP_POLARS["dataset_name"]}
            )
            assert response_3.status_code == status.HTTP_200_OK
            response_dict_3 = response_3.json()

            assert len(response_dict_3) == 1
            assert response_dict_3[0]["uid"] == str(job_opendp.uid)
            assert response_dict_3[0]["query"] == EXAMPLE_OPENDP_POLARS_PLAN
            assert response_dict_3[0]["result"] == job_opendp.result.model_dump()

    @pytest.mark.long
    @pytest.mark.skip
    def test_subsequent_budget_limit_logic(self) -> None:
        """Test_subsequent_budget_limit_logic."""
        with TestClient(get_user_app(self.config), headers=self.headers) as client:
            # Should fail: too much budget after three queries
            smartnoise_body = dict(EXAMPLE_SMARTNOISE_SQL)
            smartnoise_body["epsilon"] = 4.0

            # spend 4.0 (total_spent = 4.0 <= INTIAL_BUDGET = 10.0)
            job = submit_job_wait(client, "/smartnoise_sql_query", json=smartnoise_body)
            assert job.status == JobStatus.COMPLETE
            assert job.status_code == status.HTTP_200_OK
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.requested_by == self.user_name

            # spend 2*4.0 (total_spent = 8.0 <= INTIAL_BUDGET = 10.0)
            job = submit_job_wait(client, "/smartnoise_sql_query", json=smartnoise_body)
            assert job.status == JobStatus.COMPLETE
            assert job.status_code == status.HTTP_200_OK
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.requested_by == self.user_name

            # spend 3*4.0 (total_spent = 12.0 > INITIAL_BUDGET = 10.0)
            job = submit_job_wait(client, "/smartnoise_sql_query", json=smartnoise_body)
            assert job.status == JobStatus.FAILED
            assert job.status_code == status.HTTP_400_BAD_REQUEST
            assert job.error == LomasAPIErrorModel(
                message="Not enough budget for this query "
                + "epsilon remaining 2.0, "
                + "delta remaining 0.004970000100000034."
            )
