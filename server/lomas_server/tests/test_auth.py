import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

from lomas_client.models.config import ClientConfig
from lomas_core.models.requests_examples import example_get_admin_db_data
from lomas_server.administration.dex.dex_admin import del_all_dex_users
from lomas_server.administration.lomas_admin import drop_lomas_collection
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.app import app
from lomas_server.models.config import AdminConfig


@pytest.fixture
def demo_setup():
    lomas_demo_setup()

    yield

    admin_config = AdminConfig()
    dex_config = admin_config.dex_config
    assert dex_config is not None
    del_all_dex_users(dex_config)
    drop_lomas_collection(admin_config, "users")
    drop_lomas_collection(admin_config, "datasets")


def get_auth_header(user_name: str, user_password: str) -> dict[str, str]:
    """Fetches the access token for the user and builds the auth header."""
    # Create client config -> load token endpoint from environment variables.
    client_config = ClientConfig(user_name=user_name, user_password=user_password, dataset_name="PENGUIN")

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    oauth_client = LegacyApplicationClient(client_id="lomas_client")
    oauth2_session = OAuth2Session(client=oauth_client)

    oauth2_session.fetch_token(
        str(client_config.oidc_config.token_endpoint),
        username=client_config.user_name,
        password=client_config.user_password,
        scope=["openid", "profile", "email"],
    )

    header = {"Authorization": f"Bearer {oauth2_session.access_token}"}

    return header


def test_valid_token(demo_setup: None):
    headers = get_auth_header("dr.antartica@example.com", "dr.antartica")

    with TestClient(app, headers=headers) as client:
        response = client.post("/get_dataset_metadata", json=example_get_admin_db_data)
        assert response.status_code == status.HTTP_200_OK


def test_invalid_token():
    headers = {"Authorization": "Bearer abc"}

    with TestClient(app, headers=headers) as client:
        response = client.post("/get_dataset_metadata", json=example_get_admin_db_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {
            "type": "UnauthorizedAccessException",
            "message": "Failed bearer token verification.",
        }


def test_admin_scope(demo_setup: None) -> None:
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
