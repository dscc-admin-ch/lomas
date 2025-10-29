import os
import unittest
from pathlib import Path

from opendp.mod import enable_features

from lomas_core.models.constants import AuthenticationType
from lomas_server.models.config import Config

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005

enable_features("floating-point")


class TestSetupRootAPIEndpoint(unittest.TestCase):
    """End-to-end tests of the api endpoints."""

    def setUp(self) -> None:
        """Set Up Header and DB for test."""
        self.config = Config()

        # Disable Keycloak for UTs
        self.previous_auth_method = os.environ.get("LOMAS_SERVICE_authenticator__authentication_type", "")
        os.environ["LOMAS_SERVICE_authenticator__authentication_type"] = AuthenticationType.FREE_PASS

        self.user_name = "Dr.Antartica"
        self.bearer = 'Bearer {"name": "Dr.Antartica", "email": "dr.antartica@penguin_research.org"}'
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["Authorization"] = self.bearer

        # Fill up database if needed
        path_prefix = str(Path(__file__).parent / "test_data")

        self.config.database.add_users_via_yaml(
            yaml_file="test_user_collection.yaml",
            clean=True,
            path_prefix=path_prefix,
        )

        yaml_file = "test_datasets_with_s3.yaml"

        self.config.database.add_datasets_via_yaml(
            yaml_file=yaml_file,
            clean=True,
            path_prefix=path_prefix,
        )

    def tearDown(self) -> None:
        # Clean up database
        self.config.database.wipe()
        # reset env
        os.environ["LOMAS_SERVICE_authenticator__authentication_type"] = self.previous_auth_method
