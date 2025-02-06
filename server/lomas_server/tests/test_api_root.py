import glob
import os
import unittest

from opendp.mod import enable_features
from pymongo.database import Database

from lomas_server.admin_database.utils import get_mongodb
from lomas_server.mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)
from lomas_server.tests.constants import (
    ENV_MONGO_INTEGRATION,
    ENV_S3_INTEGRATION,
    TRUE_VALUES,
)
from lomas_server.utils.config import CONFIG_LOADER

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
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES:
            CONFIG_LOADER.load_config(
                config_path="tests/test_configs/test_config_mongo.yaml",
                secrets_path="tests/test_configs/test_secrets.yaml",
            )
        else:
            CONFIG_LOADER.load_config(
                config_path="tests/test_configs/test_config.yaml",
                secrets_path="tests/test_configs/test_secrets.yaml",
            )

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self) -> None:
        """Set Up Header and DB for test."""
        self.user_name = "Dr. Antartica"
        self.headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
        }
        self.headers["user-name"] = self.user_name

        # Fill up database if needed
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES:
            self.db: Database = get_mongodb()

            add_users_via_yaml(
                self.db,
                yaml_file="tests/test_data/test_user_collection.yaml",
                clean=True,
                overwrite=True,
            )

            if os.getenv(ENV_S3_INTEGRATION, "0").lower() in TRUE_VALUES:
                yaml_file = "tests/test_data/test_datasets_with_s3.yaml"
            else:
                yaml_file = "tests/test_data/test_datasets.yaml"

            add_datasets_via_yaml(
                self.db,
                yaml_file=yaml_file,
                clean=True,
                overwrite_datasets=True,
                overwrite_metadata=True,
            )

    def tearDown(self) -> None:
        # Clean up database if needed
        if os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES:
            drop_collection(self.db, "metadata")
            drop_collection(self.db, "datasets")
            drop_collection(self.db, "users")
            drop_collection(self.db, "queries_archives")
        else:
            for file in glob.glob("tests/test_data/local_db_file_*.yaml"):
                os.remove(file)