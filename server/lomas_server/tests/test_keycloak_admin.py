import unittest

from lomas_core.models.config import AdminConfig
from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    del_all_kc_users,
    del_kc_user,
    get_kc_admin,
)


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

    def test_add_keycloak_user(self) -> None:
        """Test adding a user in Keycloak."""
        # Delete all users to start fresh
        del_all_kc_users(self.kc_config)

        user_name = "aria"
        user_email = "aria.stark@winterfell.no"
        client_secret = "secret_aria"

        len_users_before = len(self.kc_admin.users.get())
        add_kc_user(self.kc_config, user_name, user_email, client_secret)

        # Check client is added
        new_client = self.kc_admin.clients.get(clientID=user_name)
        self.assertNotEqual(new_client, [])
        self.assertEqual(new_client[0]["name"], user_name)

        # Check users is added
        self.assertEqual(len(self.kc_admin.users.get()), len_users_before + 1)

        # Check that a user and and associated service account were created
        user_inserted = self.kc_admin.users.get(username=user_name)
        self.assertEqual(len(user_inserted), 2)

        # Check that attributes to service account is added and correct
        attributes_expected = {
            "user_email": [user_email],
            "user_name": [user_name],
            "lomas_user_client": ["true"],
        }
        self.assertEqual(user_inserted[1]["attributes"], attributes_expected)

    def test_del_keycloak_user(self) -> None:
        """Test deleting a user from Keycloak"""
        # Delete all users to start fresh
        del_all_kc_users(self.kc_config)

        # Add a fake user
        user_name = "aria"
        user_email = "aria.stark@winterfell.no"
        client_secret = "secret_aria"
        add_kc_user(self.kc_config, user_name, user_email, client_secret)

        len_users_before = len(self.kc_admin.users.get())
        client_before = self.kc_admin.clients.get(clientID=user_name)

        del_kc_user(self.kc_config, user_name)
        # Check user has been deleted
        self.assertEqual(len(self.kc_admin.users.get()), len_users_before - 1)

        # Check there is no client associated to this user
        client = self.kc_admin.clients.get(clientID=user_name)
        self.assertNotEqual(client, client_before)
