import os
import unittest
from pathlib import Path

from opendp.mod import enable_features

from lomas_core.models.config import Config
from lomas_core.models.constants import AuthenticationType
from lomas_server.administration.mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)

INITAL_EPSILON = 10
INITIAL_DELTA = 0.005

enable_features("floating-point")


class TestSetupRootAPIEndpoint(unittest.TestCase):  # pylint: disable=R0904
    """
    End-to-end tests of the api endpoints.

    This test can be both executed as an integration test
    (enabled by setting LOMAS_TEST_MONGO_INTEGRATION to True),
    or a standard test. The first requires a mongodb to be started
    before running while the latter will use a local YamlDatabase.
    """

    def setUp(self) -> None:
        """Set Up Header and DB for test."""

        # Disable Keycloak for UTs
        self.previous_auth_method = os.environ.get("lomas_service_authenticator__authentication_type", "")
        os.environ["lomas_service_authenticator__authentication_type"] = AuthenticationType.FREE_PASS

        self.user_name = "Dr.Antartica"
        self.bearer = 'Bearer {"name": "Dr.Antartica", "email": "dr.antartica@penguin_research.org"}'
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["Authorization"] = self.bearer

        # Fill up database if needed
        self.mongo_config = Config().admin_database

        path_prefix = str(Path(__file__).parent / "test_data")

        add_users_via_yaml(
            self.mongo_config,
            yaml_file="test_user_collection.yaml",
            clean=True,
            overwrite=True,
            path_prefix=path_prefix,
        )

        yaml_file = "test_datasets_with_s3.yaml"

        add_datasets_via_yaml(
            self.mongo_config,
            yaml_file=yaml_file,
            clean=True,
            overwrite_datasets=True,
            overwrite_metadata=True,
            path_prefix=path_prefix,
        )

    def tearDown(self) -> None:
        # Clean up database
        drop_collection(self.mongo_config, "metadata")
        drop_collection(self.mongo_config, "datasets")
        drop_collection(self.mongo_config, "users")
        drop_collection(self.mongo_config, "queries_archives")
        # reset env
        os.environ["lomas_service_authenticator__authentication_type"] = self.previous_auth_method
