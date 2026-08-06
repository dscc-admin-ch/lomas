import os
import posix as Status
import re

import httpx2
import pytest
from authlib.integrations.requests_client import OAuth2Session
from fastapi import status
from fastapi.testclient import TestClient
from returns.io import IOSuccess
from returns.iterables import Fold
from returns.pipeline import is_successful

from lomas_client.constants import OIDC_REQUIRED_SCOPES
from lomas_client.models.config import ClientConfig
from lomas_client.utils import raise_error
from lomas_core.exceptions import LomasAPIException, UnauthorizedAccessException
from lomas_core.models.requests_examples import EXAMPLE_GET_ADMIN_DB_DATA
from lomas_server.administration.dashboard.utils import query_lomas
from lomas_server.administration.dex.dex_admin import del_all_dex_users
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.app import app
from lomas_server.models.config import AdminConfig, Config


@pytest.fixture
def demo_setup():
    # Make sure bootstrap is enabled
    config = Config()
    config.database.set_bootstrap(config.bootstrap)

    assert lomas_demo_setup() == Status.EX_OK

    yield

    admin_config = AdminConfig()
    dex_config = admin_config.dex_config
    assert dex_config is not None
    cleanup = Fold.collect(
        [
            query_lomas(
                "/collections/datasets",
                httpx2.delete,
                headers=get_auth_header("lomas_admin@example.com", "lomas_admin"),
            ),
            query_lomas(
                "/collections/users",
                httpx2.delete,
                headers=get_auth_header("lomas_admin@example.com", "lomas_admin"),
            ),
            del_all_dex_users(dex_config),
        ],
        IOSuccess(()),
    )
    assert is_successful(cleanup)


def test_bootstrap(demo_setup: None) -> None:
    config = Config()

    # Test bootstrap creds
    with TestClient(app, headers={"Authorization": f"Bearer {config.bootstrap}"}) as client:
        response = client.get("/dataset/PENGUIN")
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/bootstrap")
        assert response.status_code == status.HTTP_200_OK

        response = client.delete("/bootstrap")
        assert response.status_code == status.HTTP_200_OK

        response = client.delete("/bootstrap")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Check response codes with proper admin headers once bootstrap removed
    with TestClient(app, headers=get_auth_header("lomas_admin@example.com", "lomas_admin")) as client:
        response = client.delete("/bootstrap")
        assert response.status_code == status.HTTP_410_GONE

        response = client.get("/bootstrap")
        assert response.status_code == status.HTTP_410_GONE


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
        response = client.post("/get_dataset_metadata", json=EXAMPLE_GET_ADMIN_DB_DATA)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("switch_query_userinfo", [True, False], indirect=True)
def test_invalid_token(switch_query_userinfo: None):
    headers = {"Authorization": "Bearer abc"}

    with TestClient(app, headers=headers) as client:
        response = client.post("/get_dataset_metadata", json=EXAMPLE_GET_ADMIN_DB_DATA)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        match_string = str(UnauthorizedAccessException("Failed bearer token verification"))
        with pytest.raises(LomasAPIException, match=re.escape(match_string)):
            raise_error(response)


@pytest.mark.parametrize("switch_query_userinfo", [True, False], indirect=True)
def test_admin_scope(demo_setup: None, switch_query_userinfo: None) -> None:
    headers = get_auth_header("lomas_admin@example.com", "lomas_admin")

    with TestClient(app, headers=headers) as client:
        response = client.get("/state")
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/get_dataset_metadata", json=EXAMPLE_GET_ADMIN_DB_DATA)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # lomas_admin user has no access to Penguin
        match_string = str(UnauthorizedAccessException("lomas_admin does not have access to PENGUIN."))
        with pytest.raises(LomasAPIException, match=re.escape(match_string)):
            raise_error(response)

    headers = get_auth_header("dr.antartica@example.com", "dr.antartica")

    with TestClient(app, headers=headers) as client:
        response = client.get("/state")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        match_string = str(UnauthorizedAccessException("Only admin users can query this endpoint."))
        with pytest.raises(LomasAPIException, match=re.escape(match_string)):
            raise_error(response)
