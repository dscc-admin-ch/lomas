import json

import opendp.prelude as dp_p
from fastapi import status
from fastapi.testclient import TestClient
from opendp.mod import enable_features
from opendp_logger import enable_logging

from lomas_core.models.exceptions import (
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)
from lomas_core.models.requests_examples import (
    PENGUIN_DATASET,
    OPENDP_PIPELINE_TYPE,
    example_dummy_opendp,
    example_opendp,
)
from lomas_core.models.responses import (
    CostResponse,
    OpenDPQueryResult,
    QueryResponse,
)
from lomas_server.app import app
from tests.test_api_root import TestSetupRootAPIEndpoint

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005

enable_features("floating-point")

class TestOpenDpEndpoint(
    TestSetupRootAPIEndpoint
):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint.
    """
    enable_logging()
    
    def test_opendp_query(self) -> None:  # pylint: disable=R0915
        """Test_opendp_query."""

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
                    "fixed_delta": None,
                    "opendp_json": transformation_pipeline.to_json(),
                    "pipeline_type": OPENDP_PIPELINE_TYPE,
                },
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message="The pipeline provided is not a "
                    + "measurement. It cannot be processed in this server."
                ).model_dump()
            )

            # Test MAX_DIVERGENCE (pure DP)
            md_pipeline = transformation_pipeline >> dp_p.m.then_laplace(scale=5.0)
            response = client.post(
                "/opendp_query",
                json={
                    "dataset_name": PENGUIN_DATASET,
                    "fixed_delta": None,
                    "opendp_json": md_pipeline.to_json(),
                    "pipeline_type": OPENDP_PIPELINE_TYPE,
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
                "fixed_delta": None,
                "pipeline_type": OPENDP_PIPELINE_TYPE,
            }
            # Should error because missing fixed_delta
            response = client.post("/opendp_query", json=json_obj)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message="fixed_delta must be set for smooth max divergence"
                    + " and zero concentrated divergence."
                ).model_dump()
            )
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
                "fixed_delta": None,
                "pipeline_type": OPENDP_PIPELINE_TYPE,
            }
            # Should error because missing fixed_delta
            response = client.post("/opendp_query", json=json_obj)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                response.json()
                == InvalidQueryExceptionModel(
                    message="fixed_delta must be set for smooth max divergence"
                    + " and zero concentrated divergence."
                ).model_dump()
            )

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
            response_model = QueryResponse.model_validate_json(response.content.decode("utf8"))
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
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to IRIS."
                ).model_dump()
            )

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
            assert (
                response.json()
                == UnauthorizedAccessExceptionModel(
                    message=f"{self.user_name} does not have access to IRIS."
                ).model_dump()
            )