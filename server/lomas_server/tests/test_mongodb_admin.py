import os
from types import SimpleNamespace
import unittest
import yaml

from pymongo import MongoClient

from admin_database.utils import get_mongodb_url
from administration.mongodb_admin import (
    add_user,
    add_user_with_budget,
    del_user,
    add_dataset_to_user,
    del_dataset_to_user,
    set_budget_field,
    set_may_query,
    add_users_via_yaml,
    add_dataset,
    add_datasets_via_yaml,
    del_dataset,
    drop_collection,
)
from constants import PrivateDatabaseType
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
        """Connection to database"""
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config_mongo.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml",
        )

        db_args = SimpleNamespace(**vars(get_config().admin_database))
        db_url = get_mongodb_url(db_args)
        cls.db = MongoClient(db_url)[db_args.db_name]

    # def setUp(self) -> None:
    #     """Connection to database"""

    def tearDown(self) -> None:
        """Drop all data from database"""
        drop_collection(self.db, "metadata")
        drop_collection(self.db, "datasets")
        drop_collection(self.db, "users")
        drop_collection(self.db, "queries_archives")

    def test_add_user(self) -> None:
        """Test adding a user"""
        user = "Tintin"

        # Add user
        add_user(self.db, user)

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
            add_user(self.db, user)

    def test_add_user_wb(self) -> None:
        """Test adding a user with a dataset"""
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10
        delta = 0.02

        add_user_with_budget(self.db, user, dataset, epsilon, delta)
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

        self.assertEqual(user_found, expected_user)

        # Adding budget to existing user should raise error
        with self.assertRaises(ValueError):
            add_user_with_budget(self.db, user, dataset, epsilon, delta)

    def test_del_user(self) -> None:
        """Test deleting a user"""
        # Setup: add a user
        user = "Tintin"
        add_user(self.db, user)

        # Deleting user
        del_user(self.db, user)

        expected_user = None
        user_found = self.db.users.find_one({"user_name": user})
        self.assertEqual(user_found, expected_user)

        # Removing non-existing should raise error
        with self.assertRaises(ValueError):
            del_user(self.db, user)

    def test_add_dataset_to_user(self) -> None:
        """Test add dataset to a user"""
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10
        delta = 0.02

        add_user(self.db, user)
        add_dataset_to_user(self.db, user, dataset, epsilon, delta)
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
        epsilon = 20
        with self.assertRaises(ValueError):
            add_dataset_to_user(self.db, user, dataset, epsilon, delta)

        # Adding dataset to non-existing user should raise an error
        user = "Milou"
        with self.assertRaises(ValueError):
            add_dataset_to_user(self.db, user, dataset, epsilon, delta)

    def test_del_dataset_to_user(self) -> None:
        """Test delete dataset from user"""
        # Setup: add user with dataset
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10
        delta = 0.02

        add_user_with_budget(self.db, user, dataset, epsilon, delta)

        # Test dataset deletion
        del_dataset_to_user(self.db, user, dataset)
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
            del_dataset_to_user(self.db, user, dataset)

        # Remove dataset not present in user should raise error
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        with self.assertRaises(Exception):
            del_dataset_to_user(self.db, user, dataset)

    def test_set_budget_field(self) -> None:
        """Test setting a budget field"""
        # Setup: add user with budget
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10
        delta = 0.02

        add_user_with_budget(self.db, user, dataset, epsilon, delta)

        # Updating budget should work
        field = "initial_epsilon"
        value = 15
        set_budget_field(self.db, user, dataset, field, value)

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
            set_budget_field(self.db, user, dataset, field, value)

        # Setting budget for non-existing dataset should fail
        user = "Tintin"
        dataset = "os de Milou"
        with self.assertRaises(ValueError):
            set_budget_field(self.db, user, dataset, field, value)

    def test_set_may_query(self) -> None:
        """Test set may query"""
        # Setup: add user with budget
        user = "Tintin"
        dataset = "PENGUIN"
        epsilon = 10
        delta = 0.02

        add_user_with_budget(self.db, user, dataset, epsilon, delta)

        # Set may query
        value = False
        set_may_query(self.db, user, value)

        expected_user = {
            "user_name": user,
            "may_query": value,
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
            set_may_query(self.db, user, value)

    def test_add_users_via_yaml(self) -> None:
        """Test create user collection via YAML file"""
        # Adding two users
        path = "./tests/test_data/test_user_collection.yaml"
        clean = False
        overwrite = False
        add_users_via_yaml(self.db, path, clean, overwrite)

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
        user = "Tintin"
        field = "initial_epsilon"
        value = 25.0
        dataset = "Bijoux de la Castafiore"
        set_budget_field(self.db, user, dataset, field, value)

        clean = True
        add_users_via_yaml(self.db, path, clean, overwrite)

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]
        self.assertEqual(user_found, tintin)

        user_found = self.db.users.find_one({"user_name": "Milou"})
        del user_found["_id"]
        self.assertEqual(user_found, milou)

        # Check overwriting (with new user)
        user = "Tintin"
        field = "initial_epsilon"
        value = False
        dataset = "Bijoux de la Castafiore"
        set_budget_field(self.db, user, dataset, field, value)

        user = "Milou"
        del_user(self.db, user)
        add_users_via_yaml(self.db, path, clean=False, overwrite=True)

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]
        self.assertEqual(user_found, tintin)

        user_found = self.db.users.find_one({"user_name": "Milou"})
        del user_found["_id"]
        self.assertEqual(user_found, milou)

        # Overwrite to false and existing users should warn
        with self.assertWarns(UserWarning):
            add_users_via_yaml(self.db, path, clean=False, overwrite=False)

    def test_add_local_dataset(self) -> None:
        """Test adding a local dataset"""
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset_name=dataset,
            database_type=database_type,
            metadata_database_type=metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )

        expected_dataset = {
            "dataset_name": dataset,
            "database_type": database_type,
            "dataset_path": dataset_path,
            "metadata": {
                "database_type": metadata_database_type,
                "metadata_path": metadata_path,
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
            {dataset: {"$exists": True}}
        )[dataset]
        self.assertEqual(metadata_found, expected_metadata)

    def test_add_datasets_via_yaml(self) -> None:
        """Test add datasets via a YAML file"""
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

        path = "./tests/test_data/test_datasets.yaml"
        clean = False
        overwrite_datasets = False
        overwrite_metadata = False

        add_datasets_via_yaml(
            self.db, path, clean, overwrite_datasets, overwrite_metadata
        )

        verify_datasets()

        # Check clean works

        # Add new dataset and then add_datasets_via_yaml with clean option
        self.db.datasets.insert_one(
            {"dataset_name": "Les aventures de Tintin"}
        )

        clean = True
        add_datasets_via_yaml(
            self.db, path, clean, overwrite_datasets, overwrite_metadata
        )
        verify_datasets()

        # Check no overwrite triggers warning
        clean = False
        with self.assertWarns(UserWarning):
            add_datasets_via_yaml(
                self.db, path, clean, overwrite_datasets, overwrite_metadata
            )

        # Check overwrite works
        self.db.datasets.update_one(
            {"dataset_name": "IRIS"}, {"$set": {"dataset_name": "IRIS"}}
        )

        overwrite_datasets = True
        add_datasets_via_yaml(
            self.db, path, clean, overwrite_datasets, overwrite_metadata
        )
        verify_datasets()

    def test_del_dataset(self) -> None:
        """Test dataset deletion"""
        # Setup: add one dataset
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset_name=dataset,
            database_type=database_type,
            metadata_database_type=metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )

        # Verify delete works
        del_dataset(self.db, dataset)

        dataset_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
        self.assertEqual(dataset_found, None)

        nb_metadata = self.db.metadata.count_documents({})
        self.assertEqual(nb_metadata, 0)

        # Delete non-existing dataset should trigger error
        with self.assertRaises(ValueError):
            del_dataset(self.db, dataset)

    def test_drop_collection(self) -> None:
        """Test drop collection from db"""
        # Setup: add one dataset
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset_name=dataset,
            database_type=database_type,
            metadata_database_type=metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )

        # Test
        collection = "datasets"
        drop_collection(self.db, collection)

        nb_datasets = self.db.datasets.count_documents({})
        self.assertEqual(nb_datasets, 0)
