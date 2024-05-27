import os
from types import SimpleNamespace
import unittest
import yaml

from pymongo import MongoClient

from admin_database.utils import get_mongodb_url
from constants import PrivateDatabaseType
from mongodb_admin import (
    add_user,
    add_user_with_budget,
    del_user,
    add_dataset_to_user,
    del_dataset_to_user,
    set_budget_field,
    set_may_query,
    create_users_collection,
    add_dataset,
    add_datasets,
    del_dataset,
    drop_collection,
)
from utils.config import get_config, CONFIG_LOADER
from tests.constants import ENV_MONGO_INTEGRATION


@unittest.skipIf(
    ENV_MONGO_INTEGRATION not in os.environ
    and os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in ("false", "0", "f"),
    f"""Not an MongoDB integration test: {ENV_MONGO_INTEGRATION}
        environment variable not set to True.""",
)
class TestMongoDBAdmin(unittest.TestCase):
    """
    Tests for the functions in mongodb_admin.py.

    This is an integration test and requires a mongodb database
    to be started before being executed.

    The test is only executed if the LOMAS_TEST_MONGO_INTEGRATION
    environment variable is set to True.
    """

    @classmethod
    def setUpClass(cls) -> None:
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config_mongo.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml",
        )

        cls.db_config = get_config().admin_database
        db_url = get_mongodb_url(cls.db_config)
        cls.db = MongoClient(db_url)[cls.db_config.db_name]

    def setUp(self) -> None:
        """_summary_"""
        self.args = SimpleNamespace(**vars(get_config().admin_database))

    def tearDown(self) -> None:
        """_summary_"""
        self.args = SimpleNamespace(**vars(get_config().admin_database))

        self.args.collection = "metadata"
        drop_collection(self.args)

        self.args.collection = "datasets"
        drop_collection(self.args)

        self.args.collection = "users"
        drop_collection(self.args)

        self.args.collection = "queries_archives"
        drop_collection(self.args)

        self.args = None  # type: ignore

    def test_add_user(self) -> None:
        """_summary_"""
        self.args.user = "Tintin"

        # Add user
        add_user(self.args)

        expected_user = {
            "user_name": self.args.user,
            "may_query": True,
            "datasets_list": [],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Adding existing user raises error
        with self.assertRaises(ValueError):
            add_user(self.args)

    def test_add_user_wb(self) -> None:
        """_summary_"""
        self.args.user = "Tintin"
        self.args.dataset = "Bijoux de la Castafiore"
        self.args.epsilon = 10
        self.args.delta = 0.02

        add_user_with_budget(self.args)
        expected_user = {
            "user_name": self.args.user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": self.args.dataset,
                    "initial_epsilon": self.args.epsilon,
                    "initial_delta": self.args.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Adding budget to existing user should raise error
        with self.assertRaises(ValueError):
            add_user_with_budget(self.args)

    def test_del_user(self) -> None:
        """_summary_"""
        # Setup: add a user
        self.args.user = "Tintin"
        add_user(self.args)

        # Deleting user
        del_user(self.args)

        expected_user = None
        user_found = self.db.users.find_one({"user_name": "Tintin"})
        self.assertEqual(user_found, expected_user)

        # Removing non-existing should raise error
        with self.assertRaises(ValueError):
            del_user(self.args)

    def test_add_dataset_to_user(self) -> None:
        """_summary_"""
        self.args.user = "Tintin"
        self.args.dataset = "Bijoux de la Castafiore"
        self.args.epsilon = 10
        self.args.delta = 0.02

        add_user(self.args)
        add_dataset_to_user(self.args)
        expected_user = {
            "user_name": self.args.user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": self.args.dataset,
                    "initial_epsilon": self.args.epsilon,
                    "initial_delta": self.args.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        assert user_found == expected_user

        # Adding dataset to existing user with existing dataset should
        # raise and error
        self.args.epsilon = 20
        with self.assertRaises(ValueError):
            add_dataset_to_user(self.args)

        # Adding dataset to non-existing user should raise an error
        self.args.user = "Milou"
        with self.assertRaises(ValueError):
            add_dataset_to_user(self.args)

    def test_del_dataset_to_user(self) -> None:
        """_summary_"""
        # Setup: add user with dataset
        self.args.user = "Tintin"
        self.args.dataset = "Bijoux de la Castafiore"
        self.args.epsilon = 10
        self.args.delta = 0.02

        add_user_with_budget(self.args)

        # Test dataset deletion
        del_dataset_to_user(self.args)
        expected_user = {
            "user_name": self.args.user,
            "may_query": True,
            "datasets_list": [],
        }
        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Remove dataset from non-existant user should raise error
        self.args.user = "Milou"

        with self.assertRaises(ValueError):
            del_dataset_to_user(self.args)

        # Remove dataset not present in user should raise error
        self.args.user = "Tintin"
        self.args.dataset = "Bijoux de la Castafiore"

        with self.assertRaises(Exception):
            del_dataset_to_user(self.args)

    def test_set_budget_field(self) -> None:
        """_summary_"""
        # Setup: add user with budget
        self.args.user = "Tintin"
        self.args.dataset = "Bijoux de la Castafiore"
        self.args.epsilon = 10
        self.args.delta = 0.02

        add_user_with_budget(self.args)

        # Updating budget should work
        self.args.field = "initial_epsilon"
        self.args.value = 15
        set_budget_field(self.args)

        expected_user = {
            "user_name": self.args.user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": self.args.dataset,
                    "initial_epsilon": self.args.value,
                    "initial_delta": self.args.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Setting budget for non-existing user should fail
        self.args.user = "Milou"

        with self.assertRaises(ValueError):
            set_budget_field(self.args)

        # Setting budget for non-existing dataset should fail
        self.args.user = "Tintin"
        self.args.dataset = "os de Milou"

        with self.assertRaises(ValueError):
            set_budget_field(self.args)

    def test_set_may_query(self) -> None:
        """_summary_"""
        # Setup: add user with budget
        self.args.user = "Tintin"
        self.args.dataset = "PENGUIN"
        self.args.epsilon = 10
        self.args.delta = 0.02

        add_user_with_budget(self.args)

        # Set may query
        self.args.value = False
        set_may_query(self.args)

        expected_user = {
            "user_name": self.args.user,
            "may_query": False,
            "datasets_list": [
                {
                    "dataset_name": self.args.dataset,
                    "initial_epsilon": self.args.epsilon,
                    "initial_delta": self.args.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Raises error when user does not exist
        self.args.user = "Milou"

        with self.assertRaises(ValueError):
            set_may_query(self.args)

    def test_create_users_collection(self) -> None:
        """_summary_"""
        # Adding two users
        self.args.path = "./tests/test_data/test_user_collection.yaml"
        self.args.clean = False
        self.args.overwrite = False
        create_users_collection(self.args)

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

        milou = {
            "user_name": "Milou",
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": "os",
                    "initial_epsilon": 20,
                    "initial_delta": 0.005,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }

        user_found = self.db.users.find_one({"user_name": "Milou"})
        del user_found["_id"]

        self.assertEqual(user_found, milou)

        # Check cleaning
        self.args.user = "Tintin"
        self.args.field = "initial_epsilon"
        self.args.value = 25.0
        self.args.dataset = "Bijoux de la Castafiore"
        set_budget_field(self.args)
        del self.args.user
        del self.args.field
        del self.args.value
        del self.args.dataset

        self.args.clean = True
        create_users_collection(self.args)

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]
        self.assertEqual(user_found, tintin)

        user_found = self.db.users.find_one({"user_name": "Milou"})
        del user_found["_id"]
        self.assertEqual(user_found, milou)

        # Check overwriting (with new user)
        self.args.user = "Tintin"
        self.args.field = "initial_epsilon"
        self.args.value = False
        self.args.dataset = "Bijoux de la Castafiore"
        set_budget_field(self.args)
        del self.args.user
        del self.args.field
        del self.args.value
        del self.args.dataset

        self.args.user = "Milou"
        del_user(self.args)

        self.args.user = None
        self.args.value = None
        self.args.clean = False
        self.args.overwrite = True
        create_users_collection(self.args)

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]
        self.assertEqual(user_found, tintin)

        user_found = self.db.users.find_one({"user_name": "Milou"})
        del user_found["_id"]
        self.assertEqual(user_found, milou)

        # Overwrite to false and existing users should warn
        self.args.overwrite = False

        with self.assertWarns(UserWarning):
            create_users_collection(self.args)

    def test_add_dataset(self) -> None:
        """_summary_"""
        self.args.dataset = "PENGUIN"
        self.args.database_type = PrivateDatabaseType.PATH
        self.args.dataset_path = "some_path"
        self.args.metadata_database_type = PrivateDatabaseType.PATH
        self.args.metadata_path = (
            "./tests/test_data/metadata/penguin_metadata.yaml"
        )

        add_dataset(self.args)

        expected_dataset = {
            "dataset_name": self.args.dataset,
            "database_type": self.args.database_type,
            "dataset_path": self.args.dataset_path,
            "metadata": {
                "database_type": self.args.metadata_database_type,
                "metadata_path": self.args.metadata_path,
            },
        }
        with open(
            "./tests/test_data/metadata/penguin_metadata.yaml",
            encoding="utf-8",
        ) as f:
            expected_metadata = yaml.safe_load(f)

        dataset_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
        del dataset_found["_id"]
        self.assertEqual(dataset_found, expected_dataset)

        metadata_found = self.db.metadata.find_one(
            {self.args.dataset: {"$exists": True}}
        )[self.args.dataset]
        self.assertEqual(metadata_found, expected_metadata)

    def test_add_datasets(self) -> None:
        """_summary_"""
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
            penguin_found = self.db.datasets.find_one(
                {"dataset_name": "PENGUIN"}
            )
            del penguin_found["_id"]
            self.assertEqual(penguin_found, penguin)

            metadata_found = self.db.metadata.find_one(
                {"PENGUIN": {"$exists": True}}
            )["PENGUIN"]
            self.assertEqual(metadata_found, penguin_metadata)

            iris_found = self.db.datasets.find_one({"dataset_name": "IRIS"})
            del iris_found["_id"]
            self.assertEqual(iris_found, iris)

            metadata_found = self.db.metadata.find_one(
                {"IRIS": {"$exists": True}}
            )["IRIS"]
            self.assertEqual(metadata_found, penguin_metadata)

        self.args.clean = False
        self.args.overwrite_datasets = False
        self.args.overwrite_metadata = False
        self.args.path = "./tests/test_data/test_datasets.yaml"

        add_datasets(self.args)

        verify_datasets()

        # Check clean works

        # Add new dataset and then add_datasets with clean option
        self.db.datasets.insert_one(
            {"dataset_name": "Les aventures de Tintin"}
        )

        self.args.clean = True
        add_datasets(self.args)
        verify_datasets()

        # Check no overwrite triggers warning
        self.args.clean = False

        with self.assertWarns(UserWarning):
            add_datasets(self.args)

        # Check overwrite works

        self.db.datasets.update_one(
            {"dataset_name": "IRIS"}, {"$set": {"dataset_name": "IRIS"}}
        )

        self.args.overwrite = True
        add_datasets(self.args)

        verify_datasets()

    def test_del_dataset(self) -> None:
        """_summary_"""
        # Setup: add one dataset
        self.args.dataset = "PENGUIN"
        self.args.database_type = PrivateDatabaseType.PATH
        self.args.dataset_path = "some_path"
        self.args.metadata_database_type = PrivateDatabaseType.PATH
        self.args.metadata_path = (
            "./tests/test_data/metadata/penguin_metadata.yaml"
        )

        add_dataset(self.args)

        # Verify delete works
        del_dataset(self.args)

        dataset_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
        self.assertEqual(dataset_found, None)

        nb_metadata = self.db.metadata.count_documents({})
        self.assertEqual(nb_metadata, 0)

        # Delete non-existing dataset should trigger error
        with self.assertRaises(ValueError):
            del_dataset(self.args)

    def test_drop_collection(self) -> None:
        """_summary_"""
        # Setup: add one dataset
        self.args.dataset = "PENGUIN"
        self.args.database_type = PrivateDatabaseType.PATH
        self.args.dataset_path = "some_path"
        self.args.metadata_database_type = PrivateDatabaseType.PATH
        self.args.metadata_path = (
            "./tests/test_data/metadata/penguin_metadata.yaml"
        )

        add_dataset(self.args)

        # Test
        self.args.collection = "datasets"
        drop_collection(self.args)

        nb_datasets = self.db.datasets.count_documents({})
        self.assertEqual(nb_datasets, 0)
