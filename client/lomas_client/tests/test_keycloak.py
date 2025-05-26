from dataclasses import dataclass

import pytest
from mantelo import KeycloakAdmin
from oauthlib import oauth2

from lomas_client import Client
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.models.config import AdminConfig, KeycloakClientConfig
from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    del_all_kc_users,
    get_kc_admin,
)


@dataclass
class TestClient:
    user_name: str = "aria"
    user_email: str = "aria.stark@winterfell.no"
    client_secret: str = "secret_aria"


@pytest.fixture
def testClient():
    return TestClient()


@dataclass(frozen=True)
class KC:
    config: KeycloakClientConfig
    admin: KeycloakAdmin


@pytest.fixture
def kc():
    """Connection to keycloak."""
    admin_config = AdminConfig()
    kc_config = admin_config.kc_config
    assert kc_config is not None

    yield KC(kc_config, get_kc_admin(kc_config))

    # Cleanup: delete all users to start fresh
    del_all_kc_users(kc_config)


def test_missing_configs() -> None:
    with pytest.raises(ValueError, match=r"Missing one of or invalid:"):
        Client()


def test_oauth2_fail_fetch_token() -> None:
    username = "Dr.Antartica"
    with pytest.raises(oauth2.InvalidClientError, match=r"Invalid client credentials"):
        Client(client_id=username, client_secret=username.lower(), dataset_name="anyName")


def test_oauth2_success(testClient, kc) -> None:
    # Add a user
    add_kc_user(kc.config, testClient.user_name, testClient.user_email, testClient.client_secret)
    client = Client(
        client_id=testClient.user_name, client_secret=testClient.client_secret, dataset_name="anyName"
    )

    with pytest.raises(UnauthorizedAccessException, match=f"User {testClient.user_name} does not exist"):
        client.get_dataset_metadata()


# Missing
# get_dataset_metadata success
# get_dummy_dataset
# get_dummy_lf
# get_initial_budget
# get_total_spent_budget
# get_remaining_budget
# get_previous_queries
