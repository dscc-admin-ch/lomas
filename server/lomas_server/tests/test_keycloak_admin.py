from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from mantelo import KeycloakAdmin
from pydantic import ValidationError
from returns.io import IOSuccess

from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    add_kc_users_via_yaml,
    del_all_kc_users,
    del_kc_user,
    get_kc_admin,
    get_kc_user_client_secret,
    set_kc_user_client_secret,
)
from lomas_server.administration.scripts.lomas_demo_setup import DemoAdminConfig
from lomas_server.administration.utils import absolute_path
from lomas_server.models.config import AdminConfig, KeycloakClientConfig


@dataclass
class Client:
    user_name: str = "aria"
    user_email: str = "aria.stark@winterfell.no"
    client_secret: str = "secret_aria"


@pytest.fixture
def client():
    return Client()


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


def test_add_keycloak_user(client, kc) -> None:
    """Test adding a user in Keycloak."""
    len_users_before = len(kc.admin.users.get())
    add_kc_user(kc.config, client.user_name, client.user_email, client.client_secret)

    # Check client is added
    new_client = kc.admin.clients.get(clientID=client.user_name)
    assert new_client != []
    assert new_client[0]["name"] == client.user_name

    # Check users is added
    assert len(kc.admin.users.get()) == len_users_before + 1

    # Check that a user and and associated service account were created
    user_inserted = kc.admin.users.get(username=client.user_name)
    assert len(user_inserted) == 2

    # Check that attributes to service account is added and correct
    attributes_expected = {
        "user_email": [client.user_email],
        "user_name": [client.user_name],
        "lomas_user_client": ["true"],
    }
    assert user_inserted[1]["attributes"] == attributes_expected


def test_del_keycloak_user(client, kc) -> None:
    """Test deleting a user from Keycloak."""
    add_kc_user(kc.config, client.user_name, client.user_email, client.client_secret)

    len_users_before = len(kc.admin.users.get())
    client_before = kc.admin.clients.get(clientID=client.user_name)

    del_kc_user(kc.config, client.user_name)
    # Check user has been deleted
    assert len(kc.admin.users.get()) == len_users_before - 1

    # Check there is no client associated to this user
    client = kc.admin.clients.get(clientID=client.user_name)
    assert client != client_before


def test_del_all_kc_users(client, kc) -> None:
    """Test deleting a user from Keycloak."""
    # Adding two users
    add_kc_user(kc.config, client.user_name, client.user_email, client.client_secret)
    add_kc_user(kc.config, client.user_name + "bis", client.user_email + "bis", client.client_secret + "bis")

    # Delete all users
    del_all_kc_users(kc.config)
    # Check users has been deleted
    assert len(kc.admin.users.get()) == 0

    # Check there are no more clients associated to each users
    assert len(kc.admin.clients.get(clientID=client.user_name)) == 0
    assert len(kc.admin.clients.get(clientID=client.user_name + "bis")) == 0


def test_get_kc_user_client_secret(client, kc):
    """Test get client secret."""
    # Add a user
    add_kc_user(kc.config, client.user_name, client.user_email, client.client_secret)

    # check if client secret is retrieved
    client_secret = get_kc_user_client_secret(kc.config, client.user_name)

    assert client_secret == IOSuccess(client.client_secret)


def test_set_kc_user_client_secret(client, kc):
    """Test set kc user client secret."""
    # Add a user
    add_kc_user(kc.config, client.user_name, client.user_email, client.client_secret)

    # Check that correct secret is added
    assert kc.admin.clients.get(clientID=client.user_name)[0]["secret"] == client.client_secret

    # Check that the secret is overwritten (and random) when not secret is given
    set_kc_user_client_secret(kc.config, client.user_name)
    assert kc.admin.clients.get(clientID=client.user_name)[0]["secret"] != client.client_secret
    assert len(kc.admin.clients.get(clientID=client.user_name)[0]["secret"]) > 0

    # Check that the new secret is overwritten correctly
    new_secret = "new_secret"
    set_kc_user_client_secret(kc.config, client.user_name, new_secret)
    assert kc.admin.clients.get(clientID=client.user_name)[0]["secret"] == new_secret


def test_add_kc_users_via_yaml(client, kc):
    """Test adding users in keycloak via a yaml file."""
    demo_config = DemoAdminConfig()

    add_kc_users_via_yaml(kc.config, demo_config.user_yaml, True, True, path_prefix=demo_config.path_prefix)
    # Check that users/clients are inserted
    assert len(kc.admin.users.get()) == 6  # check that all 6 users are inserted
    assert kc.admin.users.get(username="Dr.FSO")[0]["username"] == "dr.fso"
    assert kc.admin.users.get(username="Dr.FSO")[1]["username"] == "service-account-dr.fso"
    assert kc.admin.clients.get(clientId="Dr.FSO")[0]["attributes"]["lomas_user_client"] == "true"

    # Load demo yaml
    with Path.open(absolute_path(demo_config.user_yaml, demo_config.path_prefix), encoding="utf-8") as f:
        yaml_users = yaml.safe_load(f)
    new_secret = "test_secret"
    yaml_users["users"][0]["id"]["client_secret"] = new_secret

    # Check overwrite argument and with yaml file instead of path
    add_kc_users_via_yaml(kc.config, yaml_users, False, True)
    assert kc.admin.clients.get(clientId="Alice")[0]["secret"] == new_secret
    # Check that we have still two users (user and service account) and one client
    assert len(kc.admin.users.get(username="Alice")) == 2
    assert len(kc.admin.clients.get(clientId="Alice")) == 1

    # Check it fails if yaml does not respect pydantic model
    yaml_users["users"] = ""
    with pytest.raises(ValidationError):
        add_kc_users_via_yaml(kc.config, yaml_users, True, True)
