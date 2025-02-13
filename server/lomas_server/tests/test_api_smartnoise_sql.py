import json
import os

from fastapi import status
from fastapi.testclient import TestClient
from opendp.mod import enable_features
from tests.test_api_root import TestSetupRootAPIEndpoint

from lomas_core.models.exceptions import (
    ExternalLibraryExceptionModel,
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)
from lomas_core.models.requests_examples import (
    PENGUIN_DATASET,
    QUERY_DELTA,
    QUERY_EPSILON,
    example_dummy_smartnoise_sql,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)
from lomas_core.models.responses import (
    CostResponse,
    QueryResponse,
    SmartnoiseSQLQueryResult,
)
from lomas_server.app import app
from lomas_server.tests.constants import (
    ENV_S3_INTEGRATION,
    TRUE_VALUES,
)

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005

enable_features("floating-point")


class TestSmartnoiseSqlEndpoint(TestSetupRootAPIEndpoint):  # pylint: disable=R0904
    """
    Test Smartnoise-sql Endpoint.
    """

    def test_smartnoise_sql_query(self) -> None:
        """Test smartnoise-sql query."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            r_model = QueryResponse.model_validate(response_dict)
            assert isinstance(r_model.result, SmartnoiseSQLQueryResult)
            assert r_model.requested_by == self.user_name
            assert "NB_ROW" in r_model.result.df.columns
            assert r_model.result.df["NB_ROW"][0] > 0
            assert r_model.epsilon == QUERY_EPSILON
            assert r_model.delta >= QUERY_DELTA

            # Expect to fail: missing parameters: delta and mechanisms
            response = client.post(
                "/smartnoise_sql_query",
                json={
                    "query_str": "SELECT COUNT(*) AS NB_ROW FROM df",
                    "dataset_name": PENGUIN_DATASET,
                    "epsilon": QUERY_EPSILON,
                    "postprocess": True,
                },
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            response_dict = json.loads(response.content.decode("utf8"))["detail"]
            assert response_dict[0]["type"] == "missing"
            assert response_dict[0]["loc"] == ["body", "delta"]
            assert response_dict[1]["type"] == "missing"
            assert response_dict[1]["loc"] == ["body", "mechanisms"]

            # Expect to fail: not enough budget
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["epsilon"] = 0.000000001
            response = client.post(
                "/smartnoise_sql_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert (
                response.json()
                == ExternalLibraryExceptionModel(
                    message="Error obtaining cost: "
                    + "Noise scale is too large using epsilon=1e-09 "
                    + "and bounds (0, 1) with Mechanism.gaussian.  "
                    + "Try preprocessing to reduce senstivity, "
                    + "or try different privacy parameters.",
                    library="smartnoise_sql",
                ).model_dump()
            )

            # Expect to fail: query does not make sense
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["query_str"] = "SELECT AVG(bill) FROM df"  # no 'bill' column
            response = client.post(
                "/smartnoise_sql_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert (
                response.json()
                == ExternalLibraryExceptionModel(
                    message="Error obtaining cost: " + "Column cannot be found bill",
                    library="smartnoise_sql",
                ).model_dump()
            )

            # Expect to fail: dataset without access
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["dataset_name"] = "IRIS"
            response = client.post(
                "/smartnoise_sql_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message="Dr. Antartica does not have access to IRIS."
                ).model_dump()
            )

            # Expect to fail: dataset does not exist
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["dataset_name"] = "I_do_not_exist"
            response = client.post(
                "/smartnoise_sql_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message="Dataset I_do_not_exist does not exist. "
                    + "Please, verify the client object initialisation."
                ).model_dump()
            )

            # Expect to fail: user does not exist
            new_headers = self.headers
            new_headers["user-name"] = "I_do_not_exist"
            response = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=new_headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message="User I_do_not_exist does not exist. "
                    + "Please, verify the client object initialisation."
                ).model_dump()
            )

    def test_smartnoise_sql_query_parameters(self) -> None:
        """Test smartnoise-sql query parameters."""
        with TestClient(app, headers=self.headers) as client:
            # Change the Query
            body = dict(example_smartnoise_sql)
            body["query_str"] = "SELECT AVG(bill_length_mm) AS avg_bill_length_mm FROM df"
            response = client.post(
                "/smartnoise_sql_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            r_model = QueryResponse.model_validate(response_dict)
            assert isinstance(r_model.result, SmartnoiseSQLQueryResult)
            assert r_model.result.df["avg_bill_length_mm"].iloc[0] > 0.0

            # Change the mechanism
            body["mechanisms"] = {"count": "gaussian", "sum_float": "laplace"}
            response = client.post(
                "/smartnoise_sql_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            r_model = QueryResponse.model_validate(response_dict)
            assert isinstance(r_model.result, SmartnoiseSQLQueryResult)
            assert r_model.result.df["avg_bill_length_mm"].iloc[0] > 0.0

            # Try postprocess False
            body["postprocess"] = False
            response = client.post(
                "/smartnoise_sql_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            r_model = QueryResponse.model_validate(response_dict)
            assert isinstance(r_model.result, SmartnoiseSQLQueryResult)
            assert r_model.result.df.shape[1] == 2

    def test_smartnoise_sql_query_datetime(self) -> None:
        """Test smartnoise-sql query on datetime."""
        # Will be solved in issue 340
        # with TestClient(app, headers=self.headers) as client:
        #     # Expect to work: query with datetimes and another user
        #     new_headers = self.headers
        #     new_headers["user-name"] = "BirthdayGirl"
        #     body = dict(example_smartnoise_sql)
        #     body["dataset_name"] = "BIRTHDAYS"
        # body["query_str"] = "SELECT COUNT(*) FROM df WHERE birthday >= '1950-01-01'"
        #     response = client.post(
        #         "/smartnoise_sql_query",
        #         json=body,
        #         headers=new_headers,
        #     )
        #     data = response.content.decode("utf8")
        # assert data ==
        # df = pd.read_csv(StringIO(data))
        # assert isinstance(df, pd.DataFrame), "Response should be a pd.DataFrame"

    def test_smartnoise_sql_query_on_s3_dataset(self) -> None:
        """Test smartnoise-sql on s3 dataset."""
        if os.getenv(ENV_S3_INTEGRATION, "0").lower() in TRUE_VALUES:
            with TestClient(app, headers=self.headers) as client:
                # Expect to work
                input_smartnoise = dict(example_smartnoise_sql)
                input_smartnoise["dataset_name"] = "TINTIN_S3_TEST"
                response = client.post(
                    "/smartnoise_sql_query",
                    json=input_smartnoise,
                    headers=self.headers,
                )
                assert response.status_code == status.HTTP_200_OK

                response_dict = json.loads(response.content.decode("utf8"))
                r_model = QueryResponse.model_validate(response_dict)
                assert isinstance(r_model.result, SmartnoiseSQLQueryResult)
                assert r_model.requested_by == self.user_name
                assert "NB_ROW" in r_model.result.df.columns
                assert r_model.epsilon == QUERY_EPSILON
                assert r_model.delta >= QUERY_DELTA

    def test_dummy_smartnoise_sql_query(self) -> None:
        """Test_dummy_smartnoise_sql_query."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_smartnoise_sql_query",
                json=example_dummy_smartnoise_sql,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            r_model = QueryResponse.model_validate(response_dict)
            assert isinstance(r_model.result, SmartnoiseSQLQueryResult)
            assert r_model.result.df["NB_ROW"][0] > 0
            assert r_model.result.df["NB_ROW"][0] < 250

            # Should fail: no header
            response = client.post(
                "/dummy_smartnoise_sql_query",
                json=example_dummy_smartnoise_sql,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            response_dict = json.loads(response.content.decode("utf8"))["detail"]
            assert response_dict[0]["type"] == "missing"
            assert response_dict[0]["loc"] == ["header", "user-name"]

            # Should fail: user does not have access to dataset
            body = dict(example_dummy_smartnoise_sql)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_smartnoise_sql_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to IRIS."
                ).model_dump()
            )

    def test_smartnoise_sql_cost(self) -> None:
        """Test_smartnoise_sql_cost."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_smartnoise_sql_cost",
                json=example_smartnoise_sql_cost,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            r_model = CostResponse.model_validate(response_dict)
            assert r_model.epsilon == QUERY_EPSILON
            assert r_model.delta > QUERY_DELTA

            # Should fail: user does not have access to dataset
            body = dict(example_smartnoise_sql_cost)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_smartnoise_sql_cost",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert UnauthorizedAccessExceptionModel(message=f"{self.user_name} does not have access to IRIS.")
