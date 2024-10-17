import os
import subprocess
import unittest
from typing import List

import yaml
from lomas_core.models.collections import DSInfo, Metadata
from lomas_core.models.config import MongoDBConfig
from lomas_core.models.constants import PrivateDatabaseType
from pymongo import MongoClient

from lomas_server.admin_database.utils import get_mongodb_url
from lomas_server.tests.constants import ENV_MONGO_INTEGRATION
from lomas_server.utils.config import CONFIG_LOADER, get_config


@unittest.skipIf(
    ENV_MONGO_INTEGRATION not in os.environ
    and os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in ("false", "0", "f"),
    f"""Not an MongoDB integration test: {ENV_MONGO_INTEGRATION}
        environment variable not set to True.""",
)
class TestMongoDBAdmin(unittest.TestCase):  # pylint: disable=R0904
    """
    Tests for the functions in mongodb_admin.py.

    This is an integration test and requires a mongodb database
    to be started before being executed.

    The test is only executed if the LOMAS_TEST_MONGO_INTEGRATION
    environment variable is set to True.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Connection to database."""
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config_mongo.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml",
        )

        # Access to MongoDB
        admin_config = get_config().admin_database
        if isinstance(admin_config, MongoDBConfig):
            mongo_config: MongoDBConfig = admin_config
        else:
            raise TypeError("Loaded config does not contain a MongoDBConfig.")

        db_url = get_mongodb_url(mongo_config)
        cls.db = MongoClient(db_url)[mongo_config.db_name]

        # CLI args to connect to DB
        cls.db_connection_cli = [
            "--username",
            admin_config.username,
            "--password",
            admin_config.password,
            "--address",
            admin_config.address,
            "--port",
            str(admin_config.port),
            "--db_name",
            admin_config.db_name,
            "--db_max_pool_size",
            str(admin_config.max_pool_size),
            "--db_min_pool_size",
            str(admin_config.min_pool_size),
            "--db_max_connecting",
            str(admin_config.max_connecting),
        ]

    def tearDown(self) -> None:
        """Drop all data from database."""
        self.run_cli_command("drop_collection", ["--collection", "metadata"])
        self.run_cli_command("drop_collection", ["--collection", "datasets"])
        self.run_cli_command("drop_collection", ["--collection", "users"])
        self.run_cli_command("drop_collection", ["--collection", "queries_archives"])

    def run_cli_command(self, command: str, args: List) -> None:
        """Run a MongoDB administration CLI command.

        Args:
            command (str): The subcommand to run.
            args (List[str]): A list of arguments for the subcommand.

        Raises:
            ValueError: If the command returns a non-zero exit status.
        """
        str_args = [str(arg) for arg in args]

        cli_command = (
            ["python", "mongodb_admin_cli.py", command]
            + self.db_connection_cli
            + str_args
        )
        try:
            subprocess.run(cli_command, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            error_message = (
                f"Command: {cli_command}\n"
                f"Return Code: {e.returncode}\n"
                f"Output: {e.output.strip()}\n"
                f"Error: {e.stderr.strip()}"
            )
            raise ValueError(error_message) from e

    def test_add_user_cli(self) -> None:
        """Test adding a user via cli."""
        user = "Tintin"

        # Add user
        self.run_cli_command("add_user", ["--user", user])

        expected_user = {
            "user_name": user,
            "may_query": True,
            "datasets_list": [],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]
        self.assertEqual(user_found, expected_user)

        # Adding existing user raises error
        with self.assertRaises(ValueError):
            self.run_cli_command("add_user", ["-u", user])

        # Not giving required argument
        with self.assertRaises(ValueError):
            self.run_cli_command("add_user", ["--nope", "willfail"])

    def test_add_user_wb_cli(self) -> None:
        """Test adding a user with a dataset via cli."""
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10.0
        delta = 0.02

        self.run_cli_command(
            "add_user_with_budget",
            [
                "--user",
                user,
                "--dataset",
                dataset,
                "--epsilon",
                epsilon,
                "--delta",
                delta,
            ],
        )

        expected_user = {  # pylint: disable=duplicate-code
            "user_name": user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": dataset,
                    "initial_epsilon": epsilon,
                    "initial_delta": delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": user})
        del user_found["_id"]
        self.assertEqual(user_found, expected_user)

        # Adding budget to existing user should raise error
        with self.assertRaises(ValueError):
            self.run_cli_command(
                "add_user_with_budget",
                ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
            )

    def test_del_user_cli(self) -> None:
        """Test deleting a user via cli."""
        # Setup: add a user
        user = "Tintin"
        self.run_cli_command("add_user", ["--user", user])

        # Deleting user
        self.run_cli_command("del_user", ["--user", user])

        expected_user = None
        user_found = self.db.users.find_one({"user_name": user})
        self.assertEqual(user_found, expected_user)

        # Removing non-existing should raise error
        with self.assertRaises(ValueError):
            self.run_cli_command("del_user", ["--user", user])

    def test_add_dataset_to_user_cli(self) -> None:
        """Test add dataset to a user via cli."""
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10.0
        delta = 0.02

        self.run_cli_command("add_user", ["--user", user])
        self.run_cli_command(
            "add_dataset_to_user",
            ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
        )
        expected_user = {
            "user_name": user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": dataset,
                    "initial_epsilon": epsilon,
                    "initial_delta": delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": user})
        del user_found["_id"]

        assert user_found == expected_user

        # Adding dataset to existing user with existing dataset should
        # raise and error
        epsilon = 20.0
        with self.assertRaises(ValueError):
            self.run_cli_command(
                "add_dataset_to_user",
                ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
            )

        # Adding dataset to non-existing user should raise an error
        user = "Milou"
        with self.assertRaises(ValueError):
            self.run_cli_command(
                "add_dataset_to_user",
                ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
            )

    def test_del_dataset_to_user_cli(self) -> None:
        """Test delete dataset from user via cli."""
        # Setup: add user with dataset
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10.0
        delta = 0.02

        self.run_cli_command(
            "add_user_with_budget",
            ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
        )

        # Test dataset deletion
        self.run_cli_command("del_dataset_to_user", ["-u", user, "-d", dataset])
        expected_user = {
            "user_name": user,
            "may_query": True,
            "datasets_list": [],
        }
        user_found = self.db.users.find_one({"user_name": user})
        del user_found["_id"]
        self.assertEqual(user_found, expected_user)

        # Remove dataset from non-existant user should raise error
        user = "Milou"
        with self.assertRaises(ValueError):
            self.run_cli_command("del_dataset_to_user", ["-u", user, "-d", dataset])

        # Remove dataset not present in user should raise error
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        with self.assertRaises(Exception):
            self.run_cli_command("del_dataset_to_user", ["-u", user, "-d", dataset])

    def test_set_budget_field_cli(self) -> None:
        """Test setting a budget field via cli."""
        # Setup: add user with budget
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10.0
        delta = 0.02

        self.run_cli_command(
            "add_user_with_budget",
            ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
        )

        # Updating budget should work
        field = "initial_epsilon"
        value = 15
        self.run_cli_command(
            "set_budget_field",
            ["-u", user, "-d", dataset, "-f", field, "-v", value],
        )

        expected_user = {
            "user_name": user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": dataset,
                    "initial_epsilon": value,
                    "initial_delta": delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": user})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Setting budget for non-existing user should fail
        user = "Milou"
        with self.assertRaises(ValueError):
            self.run_cli_command(
                "set_budget_field",
                ["-u", user, "-d", dataset, "-f", field, "-v", value],
            )

        # Setting budget for non-existing dataset should fail
        user = "Tintin"
        dataset = "os de Milou"
        with self.assertRaises(ValueError):
            self.run_cli_command(
                "set_budget_field",
                ["-u", user, "-d", dataset, "-f", field, "-v", value],
            )

    def test_set_may_query_cli(self) -> None:
        """Test set may query via cli."""
        # Setup: add user with budget
        user = "Tintin"
        dataset = "PENGUIN"
        epsilon = 10.0
        delta = 0.02

        self.run_cli_command(
            "add_user_with_budget",
            ["-u", user, "-d", dataset, "-e", epsilon, "-del", delta],
        )

        # Set may query
        self.run_cli_command("set_may_query", ["-u", user, "-v", "False"])

        expected_user = {
            "user_name": user,
            "may_query": False,
            "datasets_list": [
                {
                    "dataset_name": dataset,
                    "initial_epsilon": epsilon,
                    "initial_delta": delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": user})
        del user_found["_id"]
        self.assertEqual(user_found, expected_user)

        # Raises error when user does not exist
        user = "Milou"
        with self.assertRaises(ValueError):
            self.run_cli_command("set_may_query", ["-u", user, "-v", "False"])

    def test_get_user_cli(self) -> None:
        """Test show user via CLI.

        Does not verify output for not
        """
        user = "Milou"
        self.run_cli_command("add_user", ["-u", user])
        self.run_cli_command("get_user", ["-u", user])

    def test_add_users_via_yaml_cli(self) -> None:
        """Test create user collection via YAML file via cli."""
        # Adding two users
        path = "./tests/test_data/test_user_collection.yaml"
        self.run_cli_command("add_users_via_yaml", ["-yf", path])

        tintin = {
            "user_name": "Tintin",
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": "Bijoux de la Castafiore",
                    "initial_epsilon": 10,
                    "initial_delta": 0.005,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, tintin)

    def test_get_archives_of_user_cli(self) -> None:
        """Test show archives of user via CLI.

        Does not verify output for not
        """
        user = "Milou"
        self.run_cli_command("add_user", ["-u", user])
        self.run_cli_command("get_archives_of_user", ["-u", user])

    def test_get_list_of_users_cli(self) -> None:
        """Test get list of users via CLI.

        Does not verify output for not
        """
        self.run_cli_command("get_list_of_users", [])

        self.run_cli_command("add_user", ["-u", "Milou"])
        self.run_cli_command("add_user", ["-u", "Tintin"])
        self.run_cli_command("get_list_of_users", [])

    def test_get_list_of_datasets_from_user_cli(self) -> None:
        """Test get list of users via CLI.

        Does not verify output for not
        """
        user = "Milou"
        self.run_cli_command("add_user", ["-u", user])
        self.run_cli_command("get_list_of_datasets_from_user", ["-u", user])

        self.run_cli_command(
            "add_dataset_to_user",
            ["-u", user, "-d", "os", "-e", 0.1, "-del", 0.001],
        )
        self.run_cli_command("get_list_of_datasets_from_user", ["-u", user])

    def test_add_local_dataset_cli(self) -> None:
        """Test adding a local dataset via cli."""
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        self.run_cli_command(
            "add_dataset",
            [
                "--dataset_name",
                dataset,
                "--database_type",
                database_type,
                "--dataset_path",
                dataset_path,
                "--metadata_database_type",
                metadata_database_type,
                "--metadata_path",
                metadata_path,
            ],
        )

        expected_dataset = {
            "dataset_name": dataset,
            "dataset_access": {"database_type": database_type, "path": dataset_path},
            "metadata_access": {
                "database_type": metadata_database_type,
                "path": metadata_path,
            },
        }
        expected_dataset = DSInfo.model_validate(expected_dataset).model_dump()

        with open(
            "./tests/test_data/metadata/penguin_metadata.yaml",
            encoding="utf-8",
        ) as f:
            expected_metadata = yaml.safe_load(f)
            expected_metadata = Metadata.model_validate(expected_metadata).model_dump()

        dataset_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
        del dataset_found["_id"]
        self.assertEqual(dataset_found, expected_dataset)

        metadata_found = self.db.metadata.find_one({dataset: {"$exists": True}})[
            dataset
        ]
        self.assertEqual(metadata_found, expected_metadata)

    def test_add_datasets_via_yaml_cli(self) -> None:
        """Test add datasets via a YAML file via cli."""
        # Load reference data
        with open(
            "./tests/test_data/test_datasets.yaml",
            encoding="utf-8",
        ) as f:
            datasets = yaml.safe_load(f)
            penguin = datasets["datasets"][0]
            iris = datasets["datasets"][1]

        with open(
            "./tests/test_data/metadata/penguin_metadata.yaml",
            encoding="utf-8",
        ) as f:
            penguin_metadata = yaml.safe_load(f)

        def verify_datasets():
            # Check penguin and iris are in db
            penguin_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
            del penguin_found["_id"]
            self.assertEqual(penguin_found, penguin)

            metadata_found = self.db.metadata.find_one({"PENGUIN": {"$exists": True}})[
                "PENGUIN"
            ]
            self.assertEqual(metadata_found, penguin_metadata)

            iris_found = self.db.datasets.find_one({"dataset_name": "IRIS"})
            del iris_found["_id"]
            self.assertEqual(iris_found, iris)

            metadata_found = self.db.metadata.find_one({"IRIS": {"$exists": True}})[
                "IRIS"
            ]
            self.assertEqual(metadata_found, penguin_metadata)

        path = "./tests/test_data/test_datasets.yaml"

        self.run_cli_command("add_datasets_via_yaml", ["--yaml_file", path])
        verify_datasets()

    def test_del_dataset_cli(self) -> None:
        """Test dataset deletion via cli."""
        # Setup: add one dataset
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        self.run_cli_command(
            "add_dataset",
            [
                "--dataset_name",
                dataset,
                "--database_type",
                database_type,
                "--dataset_path",
                dataset_path,
                "--metadata_database_type",
                metadata_database_type,
                "--metadata_path",
                metadata_path,
            ],
        )

        # Verify delete works
        self.run_cli_command("del_dataset", ["--dataset", dataset])

        dataset_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
        self.assertEqual(dataset_found, None)

        nb_metadata = self.db.metadata.count_documents({})
        self.assertEqual(nb_metadata, 0)

        # Delete non-existing dataset should trigger error
        with self.assertRaises(ValueError):
            self.run_cli_command("del_dataset", ["--dataset", dataset])

    def test_get_dataset_cli(self) -> None:
        """Test show dataset.

        Does not verify output for not
        """
        dataset = "PENGUIN"
        with self.assertRaises(ValueError):
            self.run_cli_command("get_dataset", ["--dataset", dataset])

        self.run_cli_command(
            "add_dataset",
            [
                "--dataset_name",
                dataset,
                "--database_type",
                PrivateDatabaseType.PATH,
                "--dataset_path",
                "some_path",
                "--metadata_database_type",
                PrivateDatabaseType.PATH,
                "--metadata_path",
                "./tests/test_data/metadata/penguin_metadata.yaml",
            ],
        )
        self.run_cli_command("get_dataset", ["--dataset", dataset])

    def test_get_metadata_of_dataset_cli(self) -> None:
        """Test show metadata_of dataset.

        Does not verify output for not
        """
        dataset = "PENGUIN"
        with self.assertRaises(ValueError):
            self.run_cli_command("get_metadata_of_dataset", ["--dataset", dataset])

        self.run_cli_command(
            "add_dataset",
            [
                "--dataset_name",
                dataset,
                "--database_type",
                PrivateDatabaseType.PATH,
                "--dataset_path",
                "some_path",
                "--metadata_database_type",
                PrivateDatabaseType.PATH,
                "--metadata_path",
                "./tests/test_data/metadata/penguin_metadata.yaml",
            ],
        )
        self.run_cli_command("get_metadata_of_dataset", ["--dataset", dataset])

    def test_get_list_of_datasets_cli(self) -> None:
        """Test get list of datasets via CLI.

        Does not verify output for not
        """
        self.run_cli_command("get_list_of_datasets", [])
        self.run_cli_command(
            "add_datasets_via_yaml",
            ["--yaml_file", "./tests/test_data/test_datasets.yaml"],
        )
        self.run_cli_command("get_list_of_datasets", [])

    def test_drop_collection_cli(self) -> None:
        """Test drop collection from db via cli."""
        # Setup: add one dataset
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        self.run_cli_command(
            "add_dataset",
            [
                "--dataset_name",
                dataset,
                "--database_type",
                database_type,
                "--dataset_path",
                dataset_path,
                "--metadata_database_type",
                metadata_database_type,
                "--metadata_path",
                metadata_path,
            ],
        )

        # Test
        collection = "datasets"
        self.run_cli_command("drop_collection", ["-c", collection])

        nb_datasets = self.db.datasets.count_documents({})
        self.assertEqual(nb_datasets, 0)

    def test_get_collection_cli(self) -> None:
        """Test show collection from db via CLI."""
        self.run_cli_command("get_collection", ["-c", "datasets"])
        self.run_cli_command(
            "add_datasets_via_yaml",
            ["--yaml_file", "./tests/test_data/test_datasets.yaml"],
        )
        self.run_cli_command("get_collection", ["-c", "datasets"])
