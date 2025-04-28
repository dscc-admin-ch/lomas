import unittest

import yaml
from pydantic import ValidationError

from lomas_core.models.config import AdminConfig
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


class TestKeycloakAdmin(unittest.TestCase):  # pylint: disable=R0904
    """
    Tests for the functions in keycloak_admin.py.

    This is an integration test and requires a keycloak instance
    to be started before being executed.
    """

    def setUp(self) -> None:
        """Connection to keycloak."""

        self.kc_config = AdminConfig().kc_config
        self.kc_admin = get_kc_admin(self.kc_config)

        self.user_name = "aria"
        self.user_email = "aria.stark@winterfell.no"
        self.client_secret = "secret_aria"

    def test_add_keycloak_user(self) -> None:
        """Test adding a user in Keycloak."""
        # Delete all users to start fresh
        del_all_kc_users(self.kc_config)

        len_users_before = len(self.kc_admin.users.get())
        add_kc_user(self.kc_config, self.user_name, self.user_email, self.client_secret)

        # Check client is added
        new_client = self.kc_admin.clients.get(clientID=self.user_name)
        self.assertNotEqual(new_client, [])
        self.assertEqual(new_client[0]["name"], self.user_name)

        # Check users is added
        self.assertEqual(len(self.kc_admin.users.get()), len_users_before + 1)

        # Check that a user and and associated service account were created
        user_inserted = self.kc_admin.users.get(username=self.user_name)
        self.assertEqual(len(user_inserted), 2)

        # Check that attributes to service account is added and correct
        attributes_expected = {
            "user_email": [self.user_email],
            "user_name": [self.user_name],
            "lomas_user_client": ["true"],
        }
        self.assertEqual(user_inserted[1]["attributes"], attributes_expected)

    def test_del_keycloak_user(self) -> None:
        """Test deleting a user from Keycloak"""
        # Delete all users to start fresh
        del_all_kc_users(self.kc_config)

        add_kc_user(self.kc_config, self.user_name, self.user_email, self.client_secret)

        len_users_before = len(self.kc_admin.users.get())
        client_before = self.kc_admin.clients.get(clientID=self.user_name)

        del_kc_user(self.kc_config, self.user_name)
        # Check user has been deleted
        self.assertEqual(len(self.kc_admin.users.get()), len_users_before - 1)

        # Check there is no client associated to this user
        client = self.kc_admin.clients.get(clientID=self.user_name)
        self.assertNotEqual(client, client_before)

    def test_del_all_kc_users(self) -> None:
        """Test deleting a user from Keycloak"""
        # Adding two users
        add_kc_user(self.kc_config, self.user_name, self.user_email, self.client_secret)
        add_kc_user(
            self.kc_config, self.user_name + "bis", self.user_email + "bis", self.client_secret + "bis"
        )

        # Delete all users
        del_all_kc_users(self.kc_config)
        # Check users has been deleted
        self.assertEqual(len(self.kc_admin.users.get()), 0)

        # Check there are no more clients associated to each users
        self.assertEqual(len(self.kc_admin.clients.get(clientID=self.user_name)), 0)
        self.assertEqual(len(self.kc_admin.clients.get(clientID=self.user_name + "bis")), 0)

    def test_get_kc_user_client_secret(self):
        """Test get client secret"""
        # Delete all users
        del_all_kc_users(self.kc_config)

        # Add a user
        add_kc_user(self.kc_config, self.user_name, self.user_email, self.client_secret)

        # check if client secret is retrieved
        client_secret = get_kc_user_client_secret(self.kc_config, self.user_name)

        self.assertEqual(client_secret, self.client_secret)

    def test_set_kc_user_client_secret(self):
        """Test set kc user client secret"""
        # Delete all users
        del_all_kc_users(self.kc_config)

        # Add a user
        add_kc_user(self.kc_config, self.user_name, self.user_email, self.client_secret)

        # Check that correct secret is added
        self.assertEqual(self.kc_admin.clients.get(clientID=self.user_name)[0]["secret"], self.client_secret)

        # Check that the secret is overwritten (and random) when not secret is given
        set_kc_user_client_secret(self.kc_config, self.user_name)
        self.assertNotEqual(
            self.kc_admin.clients.get(clientID=self.user_name)[0]["secret"], self.client_secret
        )
        self.assertTrue(len(self.kc_admin.clients.get(clientID=self.user_name)[0]["secret"]) > 0)

        # Check that the new secret is overwritten correctly
        new_secret = "new_secret"
        set_kc_user_client_secret(self.kc_config, self.user_name, new_secret)
        self.assertEqual(self.kc_admin.clients.get(clientID=self.user_name)[0]["secret"], new_secret)

    def test_add_kc_users_via_yaml(self):
        """Test adding users in keycloak via a yaml file"""
        del_all_kc_users(self.kc_config)

        demo_config = DemoAdminConfig()

        add_kc_users_via_yaml(
            self.kc_config, demo_config.user_yaml, True, True, path_prefix=demo_config.path_prefix
        )
        # Check that users/clients are inserted
        self.assertEqual(len(self.kc_admin.users.get()), 6)  # check that all 6 users are inserted
        self.assertEqual(self.kc_admin.users.get(username="Dr.FSO")[0]["username"], "dr.fso")
        self.assertEqual(self.kc_admin.users.get(username="Dr.FSO")[1]["username"], "service-account-dr.fso")
        self.assertEqual(
            self.kc_admin.clients.get(clientId="Dr.FSO")[0]["attributes"]["lomas_user_client"], "true"
        )

        # Load demo yaml
        with open(absolute_path(demo_config.user_yaml, demo_config.path_prefix), encoding="utf-8") as f:
            yaml_users: dict = yaml.safe_load(f)
        yaml_users["users"][0]["id"]["client_secret"] = "test_secret"

        # Check overwrite argument
        # seems it needs to be corrected, overwrite seems to delete users
        # add_kc_users_via_yaml(self.kc_config, yaml_users, False, True)

        # with overwrite activated
        add_kc_users_via_yaml(self.kc_config, yaml_users, True, True)
        self.assertEqual(self.kc_admin.clients.get(clientId="Alice")[0]["secret"], "test_secret")

        # Check it fails if yaml does not respect pydantic model
        yaml_users["users"] = ""
        with self.assertRaises(ValidationError):
            add_kc_users_via_yaml(self.kc_config, yaml_users, True, True)
