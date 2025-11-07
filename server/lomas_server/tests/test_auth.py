import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from lomas_client.models.config import ClientConfig
from lomas_core.models.requests_examples import example_get_admin_db_data
from lomas_server.administration.keycloak_admin import del_all_kc_users
from lomas_server.administration.lomas_admin import drop_lomas_collection
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.app import app
from lomas_server.models.config import AdminConfig


@pytest.fixture
def demo_setup():
    lomas_demo_setup()

    yield

    admin_config = AdminConfig()
    kc_config = admin_config.kc_config
    del_all_kc_users(kc_config)
    drop_lomas_collection(admin_config, "users")
    drop_lomas_collection(admin_config, "datasets")


def get_auth_header(client_id: str, client_secret: str) -> dict[str, str]:
    """Fetches the access token for the client id and builds the auth header."""
    # Create client config -> load token endpoint from environment variables.
    client_config = ClientConfig(client_id=client_id, client_secret=client_secret, dataset_name="PENGUIN")

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    oauth_client = BackendApplicationClient(client_id=client_config.client_id)
    oauth2_session = OAuth2Session(client=oauth_client)

    oauth2_session.fetch_token(
        client_config.token_endpoint,
        client_id=client_config.client_id,
        client_secret=client_config.client_secret,
    )

    header = {"Authorization": f"Bearer {oauth2_session.access_token}"}

    return header


def test_valid_token(demo_setup: None):

    headers = get_auth_header("Dr.Antartica", "dr.antartica")

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

    headers = get_auth_header("lomas_admin", "lomas_admin")

    with TestClient(app, headers=headers) as client:
        response = client.get("/state")
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/get_dataset_metadata", json=example_get_admin_db_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # lomas_admin user has no user_email attribute, server cannot build proper UserId.
        assert response.json() == {
            "type": "UnauthorizedAccessException",
            "message": "Failed bearer token verification.",
        }

    headers = get_auth_header("Dr.Antartica", "dr.antartica")

    with TestClient(app, headers=headers) as client:
        response = client.get("/state")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {
            "type": "UnauthorizedAccessException",
            "message": "Only admin user can query this endpoint.",
        }
