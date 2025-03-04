import unittest

from opendp.mod import enable_features

from lomas_server.administration.mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)
from lomas_server.utils.config import CONFIG_LOADER, get_config

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

    @classmethod
    def setUpClass(cls) -> None:
        # Read correct config depending on the database we test against
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config_mongo.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self) -> None:
        """Set Up Header and DB for test."""

        self.user_name = "Dr.Antartica"
        self.bearer = 'Bearer {"name": "Dr.Antartica", "email": "dr.antartica@penguin_research.org"}'
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["Authorization"] = self.bearer

        # Fill up database if needed
        self.mongo_config = get_config().admin_database

        add_users_via_yaml(
            self.mongo_config,
            yaml_file="tests/test_data/test_user_collection.yaml",
            clean=True,
            overwrite=True,
        )

        yaml_file = "tests/test_data/test_datasets_with_s3.yaml"

        add_datasets_via_yaml(
            self.mongo_config,
            yaml_file=yaml_file,
            clean=True,
            overwrite_datasets=True,
            overwrite_metadata=True,
        )

    def tearDown(self) -> None:
        # Clean up database
        drop_collection(self.mongo_config, "metadata")
        drop_collection(self.mongo_config, "datasets")
        drop_collection(self.mongo_config, "users")
        drop_collection(self.mongo_config, "queries_archives")
