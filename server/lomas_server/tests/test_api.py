import glob
import json
import os
import unittest

import numpy as np
import opendp.prelude as dp_p
from fastapi import status
from fastapi.testclient import TestClient
from lomas_core.constants import DPLibraries
from lomas_core.error_handler import InternalServerException
from lomas_core.models.config import DBConfig
from lomas_core.models.responses import (
    CostResponse,
    DummyDsResponse,
    InitialBudgetResponse,
    OpenDPQueryResult,
    QueryResponse,
    RemainingBudgetResponse,
    SmartnoiseSQLQueryResult,
    SpentBudgetResponse,
)
from opendp.mod import enable_features
from opendp_logger import enable_logging
from pymongo.database import Database

from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.admin_database.utils import get_mongodb
from lomas_server.app import app
from lomas_server.mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)
from lomas_server.tests.constants import (
    ENV_MONGO_INTEGRATION,
    ENV_S3_INTEGRATION,
    TRUE_VALUES,
)
from lomas_server.utils.config import CONFIG_LOADER
from lomas_server.utils.query_examples import (
    DUMMY_NB_ROWS,
    PENGUIN_DATASET,
    QUERY_DELTA,
    QUERY_EPSILON,
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

enable_features("floating-point")


class TestRootAPIEndpoint(unittest.TestCase):  # pylint: disable=R0904
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
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES:
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
        """Set Up Header and DB for test."""
        self.user_name = "Dr. Antartica"
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["user-name"] = self.user_name

        # Fill up database if needed
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES:
            self.db: Database = get_mongodb()

            add_users_via_yaml(
                self.db,
                yaml_file="tests/test_data/test_user_collection.yaml",
                clean=True,
                overwrite=True,
            )

            if os.getenv(ENV_S3_INTEGRATION, "0").lower() in TRUE_VALUES:
                yaml_file = "tests/test_data/test_datasets_with_s3.yaml"
            else:
                yaml_file = "tests/test_data/test_datasets.yaml"

            add_datasets_via_yaml(
                self.db,
                yaml_file=yaml_file,
                clean=True,
                overwrite_datasets=True,
                overwrite_metadata=True,
            )

    def tearDown(self) -> None:
        # Clean up database if needed
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES:
            drop_collection(self.db, "metadata")
            drop_collection(self.db, "datasets")
            drop_collection(self.db, "users")
            drop_collection(self.db, "queries_archives")
        else:
            for file in glob.glob("tests/test_data/local_db_file_*.yaml"):
                os.remove(file)

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
            assert response.json() == {
                "InvalidQueryException": f"Dataset {fake_dataset} does not "
                + "exist. Please, verify the client object initialisation."
            }

            # Expect to fail: user does have access to dataset
            other_dataset = "IRIS"
            response = client.post(
                "/get_dataset_metadata",
                json={"dataset_name": other_dataset},
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to {other_dataset}."
            }

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
            ).all(), (
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
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": f"Dataset {fake_dataset} does not "
                + "exist. Please, verify the client object initialisation."
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
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to {other_dataset}."
            }

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
            assert response.json() == {
                "UnauthorizedAccessException": f"User {fake_user} does not "
                + "exist. Please, verify the client object initialisation."
            }

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

            assert (
                r_model.dummy_df.shape[0] == 10
            ), "Dummy pd.DataFrame does not have expected number of rows"

            expected_dtype = np.dtype("<M8[ns]")
            assert (
                r_model.dummy_df.dtypes.values[0] == expected_dtype
            ), f"Dtypes do not match: {r_model.dummy_df.dtypes} != {expected_dtype}"

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
            assert response.json() == {
                "ExternalLibraryException": "Error obtaining cost: "
                + "Noise scale is too large using epsilon=1e-09 "
                + "and bounds (0, 1) with Mechanism.gaussian.  "
                + "Try preprocessing to reduce senstivity, "
                + "or try different privacy parameters.",
                "library": "smartnoise_sql",
            }

            # Expect to fail: query does not make sense
            input_smartnoise = dict(example_smartnoise_sql)
            input_smartnoise["query_str"] = (
                "SELECT AVG(bill) FROM df"  # no 'bill' column
            )
            response = client.post(
                "/smartnoise_sql_query",
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
                "/smartnoise_sql_query",
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
                "/smartnoise_sql_query",
                json=input_smartnoise,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "Dataset I_do_not_exist does not exist. "
                + "Please, verify the client object initialisation."
            }

            # Expect to fail: user does not exist
            new_headers = self.headers
            new_headers["user-name"] = "I_do_not_exist"
            response = client.post(
                "/smartnoise_sql_query",
                json=example_smartnoise_sql,
                headers=new_headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + "User I_do_not_exist does not exist. "
                + "Please, verify the client object initialisation."
            }

    def test_smartnoise_sql_query_parameters(self) -> None:
        """Test smartnoise-sql query parameters."""
        with TestClient(app, headers=self.headers) as client:
            # Change the Query
            body = dict(example_smartnoise_sql)
            body["query_str"] = (
                "SELECT AVG(bill_length_mm) AS avg_bill_length_mm FROM df"
            )
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
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": "User None does not exist."
                + " Please, verify the client object initialisation."
            }

            # Should fail: user does not have access to dataset
            body = dict(example_dummy_smartnoise_sql)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_smartnoise_sql_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

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
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_opendp_query(self) -> None:  # pylint: disable=R0915
        """Test_opendp_query."""
        enable_logging()

        with TestClient(app, headers=self.headers) as client:
            # Basic test based on example with max divergence (Pure DP)
            response = client.post(
                "/opendp_query",
                json=example_opendp,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = QueryResponse.model_validate(response_dict)
            assert response_model.requested_by == self.user_name
            assert isinstance(response_model.result, OpenDPQueryResult)
            assert not isinstance(response_model.result.value, list)
            assert response_model.result.value > 0
            assert response_model.epsilon > 0.1
            assert response_model.delta == 0

            # Tests on different pipeline
            colnames = [
                "species",
                "island",
                "bill_length_mm",
                "bill_depth_mm",
                "flipper_length_mm",
                "body_mass_g",
                "sex",
            ]
            transformation_pipeline = (
                dp_p.t.make_split_dataframe(separator=",", col_names=colnames)
                >> dp_p.t.make_select_column(key="bill_length_mm", TOA=str)
                >> dp_p.t.then_cast_default(TOA=float)
                >> dp_p.t.then_clamp(bounds=(30.0, 65.0))
                >> dp_p.t.then_resize(size=346, constant=43.61)
                >> dp_p.t.then_variance()
            )

            # Expect to fail: transormation instead of measurement
            response = client.post(
                "/opendp_query",
                json={
                    "dataset_name": PENGUIN_DATASET,
                    "opendp_json": transformation_pipeline.to_json(),
                },
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": "The pipeline provided is not a "
                + "measurement. It cannot be processed in this server."
            }

            # Test MAX_DIVERGENCE (pure DP)
            md_pipeline = transformation_pipeline >> dp_p.m.then_laplace(scale=5.0)
            response = client.post(
                "/opendp_query",
                json={
                    "dataset_name": PENGUIN_DATASET,
                    "opendp_json": md_pipeline.to_json(),
                },
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = QueryResponse.model_validate(response_dict)
            assert response_model.requested_by == self.user_name
            assert isinstance(response_model.result, OpenDPQueryResult)
            assert not isinstance(response_model.result.value, list)
            assert response_model.result.value > 0
            assert response_model.epsilon > 0.1
            assert response_model.delta == 0

            # Test ZERO_CONCENTRATED_DIVERGENCE
            zcd_pipeline = transformation_pipeline >> dp_p.m.then_gaussian(scale=5.0)
            json_obj = {
                "dataset_name": PENGUIN_DATASET,
                "opendp_json": zcd_pipeline.to_json(),
            }
            # Should error because missing fixed_delta
            response = client.post("/opendp_query", json=json_obj)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "fixed_delta must be set for smooth max divergence"
                + " and zero concentrated divergence."
            }
            # Should work because fixed_delta is set
            json_obj["fixed_delta"] = 1e-6
            response = client.post("/opendp_query", json=json_obj)
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = QueryResponse.model_validate(response_dict)
            assert response_model.requested_by == self.user_name
            assert isinstance(response_model.result, OpenDPQueryResult)
            assert not isinstance(response_model.result.value, list)
            assert response_model.result.value > 0
            assert response_model.epsilon > 0.1
            assert response_model.delta == 1e-6

            # Test SMOOTHED_MAX_DIVERGENCE (approx DP)
            sm_pipeline = dp_p.c.make_zCDP_to_approxDP(zcd_pipeline)
            json_obj = {
                "dataset_name": PENGUIN_DATASET,
                "opendp_json": sm_pipeline.to_json(),
            }
            # Should error because missing fixed_delta
            response = client.post("/opendp_query", json=json_obj)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {
                "InvalidQueryException": ""
                + "fixed_delta must be set for smooth max divergence"
                + " and zero concentrated divergence."
            }

            # Should work because fixed_delta is set
            json_obj["fixed_delta"] = 1e-6
            response = client.post("/opendp_query", json=json_obj)
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            response_model = QueryResponse.model_validate(response_dict)
            assert response_model.requested_by == self.user_name
            assert isinstance(response_model.result, OpenDPQueryResult)
            assert not isinstance(response_model.result.value, list)
            assert response_model.result.value > 0
            assert response_model.epsilon > 0.1
            assert response_model.delta == 1e-6

            # # Test FIXED_SMOOTHED_MAX_DIVERGENCE
            # fms_pipeline = (
            #     dp_p.t.make_split_dataframe(separator=",", col_names=colnames)
            #     >> dp_p.t.make_select_column(key="island", TOA=str)
            #     >> dp_p.t.then_count_by(MO=dp_p.L1Distance[float], TV=float)
            #     >> dp_p.m.then_base_laplace_threshold(
            #         scale=2.0, threshold=28.0
            #     )
            # )
            # json_obj = {
            #     "dataset_name": PENGUIN_DATASET,
            #     "opendp_json": fms_pipeline.to_json(),
            # }
            # # Should error because missing fixed_delta
            # response = client.post("/opendp_query", json=json_obj)
            # assert response.status_code == status.HTTP_200_OK
            # response_dict = json.loads(response.content.decode("utf8"))
            # assert response_dict["requested_by"] == self.user_name
            # assert isinstance(response_dict["query_response"], dict)
            # assert response_dict["spent_epsilon"] > 0.1
            # assert response_dict["spent_delta"] > 0

    def test_dummy_opendp_query(self) -> None:
        """Test_dummy_opendp_query."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_opendp_query",
                json=example_dummy_opendp,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK
            response_model = QueryResponse.model_validate_json(
                response.content.decode("utf8")
            )
            assert response_model.requested_by == self.user_name
            assert isinstance(response_model.result, OpenDPQueryResult)
            assert not isinstance(response_model.result.value, list)
            assert response_model.result.value > 0

            # Should fail: user does not have access to dataset
            body = dict(example_dummy_opendp)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_opendp_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_opendp_cost(self) -> None:
        """Test_opendp_cost."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_opendp_cost",
                json=example_opendp,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            response_model = CostResponse.model_validate(response_dict)
            assert response_model.epsilon > 0.1
            assert response_model.delta == 0

            # Should fail: user does not have access to dataset
            body = dict(example_opendp)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_opendp_cost",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_get_initial_budget(self) -> None:
        """Test_get_initial_budget."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_initial_budget", json=example_get_admin_db_data
            )
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
            response_2 = client.post(
                "/get_initial_budget", json=example_get_admin_db_data
            )
            assert response_2.status_code == status.HTTP_200_OK
            response_dict_2 = json.loads(response_2.content.decode("utf8"))
            assert response_dict_2 == response_dict

    def test_get_total_spent_budget(self) -> None:
        """Test_get_total_spent_budget."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/get_total_spent_budget", json=example_get_admin_db_data
            )
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
            response_2 = client.post(
                "/get_total_spent_budget", json=example_get_admin_db_data
            )
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
            response = client.post(
                "/get_remaining_budget", json=example_get_admin_db_data
            )
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
            response_2 = client.post(
                "/get_remaining_budget", json=example_get_admin_db_data
            )
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
            response = client.post(
                "/get_previous_queries", json=example_get_admin_db_data
            )
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
            assert response_dict_2["previous_queries"][0]["response"] == query_res

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
                response_dict_3["previous_queries"][1]["client_input"] == example_opendp
            )
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
            assert response.json() == {
                "InvalidQueryException": "Not enough budget for this query "
                + "epsilon remaining 2.0, "
                + "delta remaining 0.004970000100000034."
            }
