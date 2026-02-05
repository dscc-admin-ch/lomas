from dataclasses import dataclass

import pytest
import requests
import yaml

from lomas_core.models.collections import UserCollection
from lomas_server.administration.dex.api.api_pb2 import DiscoveryReq, ListPasswordReq
from lomas_server.administration.dex.api.api_pb2_grpc import DexStub
from lomas_server.administration.dex.dex_admin import (
    add_dex_user,
    add_dex_users,
    add_dex_users_via_yaml,
    del_all_dex_users,
    del_dex_user,
    get_grpc_channel,
    set_dex_user_password,
)
from lomas_server.administration.scripts.lomas_demo_setup import DemoAdminConfig
from lomas_server.models.config import AdminConfig, DexAdminConfig


@dataclass
class Client:
    user_name: str = "aria"
    user_email: str = "aria.stark@winterfell.no"
    password: str = "secret_aria"


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def dex_config():
    """Dex config.

    Removes all dex users before yield.
    """
    admin_config = AdminConfig()
    dex_config = admin_config.dex_config
    assert dex_config is not None
    # Cleanup for tests
    del_all_dex_users(dex_config)

    yield dex_config

    # Cleanup: delete all users to start fresh
    del_all_dex_users(dex_config)


def get_dex_passwords(dex_config: DexAdminConfig):
    """Util function to get all passwords from dex."""
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)
        return stub.ListPasswords(ListPasswordReq()).passwords


def test_add_dex_user(client, dex_config) -> None:
    """Test adding a user in Dex."""
    len_users_before = len(get_dex_passwords(dex_config))

    add_dex_user(dex_config, client.user_name, client.user_email, client.password)

    # Check user is added
    users_after = get_dex_passwords(dex_config)
    len_users_after = len(users_after)

    assert len_users_before == len_users_after - 1

    for user in users_after:
        if user.username == client.user_name:
            assert user.email == client.user_email
            return

    raise AssertionError("Could not find added users.")


def test_del_dex_user(client, dex_config) -> None:
    """Test deleting a user from Dex."""
    add_dex_user(dex_config, "no-delete", "no-delete@example.no", "no-delete")
    add_dex_user(dex_config, client.user_name, client.user_email, client.password)

    len_users_before = len(get_dex_passwords(dex_config))

    del_dex_user(dex_config, client.user_name)
    # Check user has been deleted
    users_after = get_dex_passwords(dex_config)
    len_users_after = len(users_after)
    assert len_users_after == len_users_before - 1

    # Check correct user was deleted
    assert users_after[0].username == "no-delete"


def test_del_all_dex_users(client, dex_config) -> None:
    """Test deleting a user from Dex."""
    # Adding two users
    add_dex_user(dex_config, client.user_name, client.user_email, client.password)
    add_dex_user(dex_config, client.user_name + "bis", client.user_email + "bis", client.password + "bis")

    # Delete all users
    del_all_dex_users(dex_config)
    # Check users has been deleted
    assert len(get_dex_passwords(dex_config)) == 0


def test_set_dex_user_password(client, dex_config):
    """Test set kc user client secret."""
    # Add a user
    add_dex_user(dex_config, client.user_name, client.user_email, client.password)
    set_dex_user_password(dex_config, client.user_name, "new_password")

    # Get token via password grant to verify password is correctly set.
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)
        token_endpoint = stub.GetDiscovery(DiscoveryReq()).token_endpoint

    token = requests.post(
        token_endpoint,
        data={
            "client_id": "lomas_client",  # assumes this client exists
            "grant_type": "password",
            "scope": "openid profile email",
            "username": client.user_email,
            "password": "new_password",
            "audience": "lomas_client",
        },
    )
    assert token.status_code == 200


def test_add_dex_users_via_yaml(client, dex_config):
    """Test adding users in dex via a yaml file."""
    len_users_before = len(get_dex_passwords(dex_config))

    demo_config = DemoAdminConfig()
    add_dex_users_via_yaml(
        dex_config, demo_config.path_prefix / demo_config.user_yaml.relative_to("/"), True, True
    )
    # Check that users/clients are inserted
    users_after = get_dex_passwords(dex_config)
    assert len(users_after) == len_users_before + 7  # check that all 6 users are inserted

    # Load demo yaml
    yaml_users = yaml.safe_load((demo_config.path_prefix / demo_config.user_yaml.relative_to("/")).open())
    new_email = "new@email.com"
    yaml_users["users"][0]["id"]["email"] = new_email

    # Check overwrite argument and with yaml file instead of path
    add_dex_users(dex_config, UserCollection(**yaml_users), False, True)
    users_after = get_dex_passwords(dex_config)
    for user in users_after:
        if user.username == "Alice":
            assert user.email == new_email
