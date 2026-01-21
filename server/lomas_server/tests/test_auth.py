import os

import pytest
from authlib.integrations.requests_client import OAuth2Session
from fastapi import status
from fastapi.testclient import TestClient

from lomas_client.constants import OIDC_REQUIRED_SCOPES
from lomas_client.models.config import ClientConfig
from lomas_core.models.requests_examples import example_get_admin_db_data
from lomas_server.administration.dex.dex_admin import del_all_dex_users
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.app import app
from lomas_server.models.config import AdminConfig, Config


@pytest.fixture
def demo_setup():
    lomas_demo_setup()

    yield

    admin_config = AdminConfig()
    db = Config().database
    dex_config = admin_config.dex_config
    assert dex_config is not None
    del_all_dex_users(dex_config)
    db.drop_collection("users")
    db.drop_collection("datasets")


def get_auth_header(user_name: str, user_password: str) -> dict[str, str]:
    """Fetches the access token for the user and builds the auth header."""
    # Create client config -> load token endpoint from environment variables.
    client_config = ClientConfig(user_name=user_name, user_password=user_password, dataset_name="PENGUIN")

    oauth2_session = OAuth2Session(
        client_id="lomas_client",
        token_endpoint=client_config.oidc_config.token_endpoint,
        token_endpoint_auth_method="none",
        scope=OIDC_REQUIRED_SCOPES,
        leeway=30,  # refresh token 30 seconds before expiry
    )

    oauth2_session.fetch_token(
        str(client_config.oidc_config.token_endpoint),
        username=user_name,
        password=user_password,
        grant_type="password",
    )

    header = {"Authorization": f"Bearer {oauth2_session.token['access_token']}"}

    return header


@pytest.fixture
def switch_query_userinfo(request):
    userinfo_key = "LOMAS_SERVICE_authenticator__query_userinfo"
    if request.param:
        query_userinfo = os.getenv(userinfo_key)
        assert isinstance(query_userinfo, str)
        # pydantic allow true/false/True/False
        os.environ[userinfo_key] = str(query_userinfo == "true")

    yield

    if request.param:
        os.environ[userinfo_key] = query_userinfo


@pytest.mark.parametrize("switch_query_userinfo", [True, False], indirect=True)
def test_valid_token(demo_setup: None, switch_query_userinfo: None):
    headers = get_auth_header("dr.antartica@example.com", "dr.antartica")

    with TestClient(app, headers=headers) as client:
        response = client.post("/get_dataset_metadata", json=example_get_admin_db_data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("switch_query_userinfo", [True, False], indirect=True)
def test_invalid_token(switch_query_userinfo: None):
    headers = {"Authorization": "Bearer abc"}

    with TestClient(app, headers=headers) as client:
        response = client.post("/get_dataset_metadata", json=example_get_admin_db_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {
            "type": "UnauthorizedAccessException",
            "message": "Failed bearer token verification.",
        }


@pytest.mark.parametrize("switch_query_userinfo", [True, False], indirect=True)
def test_admin_scope(demo_setup: None, switch_query_userinfo: None) -> None:
    headers = get_auth_header("lomas_admin@example.com", "lomas_admin")

    with TestClient(app, headers=headers) as client:
        response = client.get("/state")
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/get_dataset_metadata", json=example_get_admin_db_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # lomas_admin user has no access to Penguin
        assert response.json() == {
            "type": "UnauthorizedAccessException",
            "message": "lomas_admin does not have access to PENGUIN.",
        }

    headers = get_auth_header("dr.antartica@example.com", "dr.antartica")

    with TestClient(app, headers=headers) as client:
        response = client.get("/state")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {
            "type": "UnauthorizedAccessException",
            "message": "Only admin users can query this endpoint.",
        }
