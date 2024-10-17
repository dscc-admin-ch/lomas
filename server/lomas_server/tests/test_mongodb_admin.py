import os
import unittest
from typing import Dict

import boto3
import yaml
from lomas_core.models.collections import DSInfo, Metadata
from lomas_core.models.config import MongoDBConfig
from lomas_core.models.constants import PrivateDatabaseType
from pymongo import MongoClient

from lomas_server.admin_database.utils import (
    add_demo_data_to_mongodb_admin,
    get_mongodb_url,
)
from lomas_server.mongodb_admin import (
    add_dataset,
    add_dataset_to_user,
    add_datasets_via_yaml,
    add_user,
    add_user_with_budget,
    add_users_via_yaml,
    del_dataset,
    del_dataset_to_user,
    del_user,
    drop_collection,
    get_archives_of_user,
    get_collection,
    get_dataset,
    get_list_of_datasets,
    get_list_of_datasets_from_user,
    get_list_of_users,
    get_metadata_of_dataset,
    get_user,
    set_budget_field,
    set_may_query,
)
from lomas_server.tests.constants import (
    ENV_MONGO_INTEGRATION,
    ENV_S3_INTEGRATION,
    FALSE_VALUES,
    TRUE_VALUES,
)
from lomas_server.utils.config import CONFIG_LOADER, get_config


@unittest.skipIf(
    ENV_MONGO_INTEGRATION not in os.environ
    and os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in FALSE_VALUES,
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
            mongo_config = admin_config
        else:
            raise TypeError("Loaded config does not contain a MongoDBConfig.")

        db_url = get_mongodb_url(mongo_config)
        cls.db = MongoClient(db_url)[mongo_config.db_name]

    def tearDown(self) -> None:
        """Drop all data from database."""
        drop_collection(self.db, "metadata")
        drop_collection(self.db, "datasets")
        drop_collection(self.db, "users")
        drop_collection(self.db, "queries_archives")

    def test_add_user(self) -> None:
        """Test adding a user."""
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
        """Test adding a user with a dataset."""
        user = "Tintin"
        dataset = "Bijoux de la Castafiore"
        epsilon = 10
        delta = 0.02

        add_user_with_budget(self.db, user, dataset, epsilon, delta)
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
            add_user_with_budget(self.db, user, dataset, epsilon, delta)

    def test_del_user(self) -> None:
        """Test deleting a user."""
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
        """Test add dataset to a user."""
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
        """Test delete dataset from user."""
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
        """Test setting a budget field."""
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
        """Test set may query."""
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

    def test_get_user(self) -> None:
        """Test show user."""
        user = "Milou"
        dataset = "os"
        epsilon = 20
        delta = 0.005
        add_user_with_budget(self.db, user, dataset, epsilon, delta)
        user_found = get_user(self.db, "Milou")
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
        self.assertEqual(user_found, expected_user)

        with self.assertRaises(ValueError):
            user_found = get_user(self.db, "Bianca Castafiore")

    def test_add_users_via_yaml(self) -> None:
        """Test create user collection via YAML file."""
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

    def test_get_archives_of_user(self) -> None:
        """Test show archives of user."""
        add_user(self.db, "Milou")
        add_user(self.db, "Tintin")

        # User exist but empty
        archives_found = get_archives_of_user(self.db, "Milou")
        expected_archives: list[Dict] = []
        self.assertEqual(archives_found, expected_archives)

        # User does not exist
        with self.assertRaises(ValueError):
            archives_found = get_archives_of_user(self.db, "Bianca Castafiore")

        # Add archives for Tintin and Dr. Antartica
        path = "./tests/test_data/test_archives_collection.yaml"
        with open(path, encoding="utf-8") as f:
            archives = yaml.safe_load(f)
        self.db.queries_archives.insert_many(archives)

        # Milou still empty
        archives_found = get_archives_of_user(self.db, "Milou")
        expected_archives = []
        self.assertEqual(archives_found, expected_archives)

        # Tintin has archives
        archives_found = get_archives_of_user(self.db, "Tintin")[0]
        expected_archives = archives[1]

        archives_found.pop("_id")
        if isinstance(expected_archives, dict):
            expected_archives.pop("_id")

        self.assertEqual(archives_found, expected_archives)

    def test_get_list_of_users(self) -> None:
        """Test get list of users."""
        users_list = get_list_of_users(self.db)
        self.assertEqual(users_list, [])

        dataset = "Bijoux de la Castafiore"
        epsilon = 0.1
        delta = 0.0001
        add_user(self.db, "Bianca Castafiore")
        add_user_with_budget(self.db, "Tintin", dataset, epsilon, delta)
        add_user_with_budget(self.db, "Milou", dataset, epsilon, delta)
        users_list = get_list_of_users(self.db)
        self.assertEqual(users_list, ["Bianca Castafiore", "Tintin", "Milou"])

    def test_get_list_of_datasets_from_users(self) -> None:
        """Test get list of datasets from users."""
        user = "Bianca Castafiore"
        add_user(self.db, user)

        users_list = get_list_of_datasets_from_user(self.db, user)
        self.assertEqual(users_list, [])

        epsilon = 0.1
        delta = 0.0001
        add_dataset_to_user(self.db, user, "Bijoux de la Castafiore", epsilon, delta)
        add_dataset_to_user(self.db, user, "Le Sceptre d'Ottokar", epsilon, delta)
        add_dataset_to_user(self.db, user, "Les Sept Boules de cristal", epsilon, delta)
        add_user_with_budget(self.db, "Milou", "os", 0.1, 0.001)

        dataset_list = get_list_of_datasets_from_user(self.db, user)
        self.assertEqual(
            dataset_list,
            [
                "Bijoux de la Castafiore",
                "Le Sceptre d'Ottokar",
                "Les Sept Boules de cristal",
            ],
        )

        dataset_list = get_list_of_datasets_from_user(self.db, "Milou")
        self.assertEqual(dataset_list, ["os"])

    def test_add_local_dataset(self) -> None:
        """Test adding a local dataset."""
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
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

        # Add already present dataset
        with self.assertRaises(ValueError):
            add_dataset(
                self.db,
                dataset,
                database_type=database_type,
                metadata_database_type=metadata_database_type,
                dataset_path=dataset_path,
                metadata_path=metadata_path,
            )

        # Add not already present dataset but present metadata
        drop_collection(self.db, "datasets")
        with self.assertRaises(ValueError):
            add_dataset(
                self.db,
                dataset,
                database_type=database_type,
                metadata_database_type=metadata_database_type,
                dataset_path=dataset_path,
                metadata_path=metadata_path,
            )

        # Restart clean
        drop_collection(self.db, "metadata")
        drop_collection(self.db, "datasets")

        # Unknown database type for dataset
        with self.assertRaises(ValueError):
            add_dataset(
                self.db,
                dataset,
                database_type="type_that_does_not_exist",
                metadata_database_type=metadata_database_type,
                dataset_path=dataset_path,
                metadata_path=metadata_path,
            )

        # Unknown database type for metadata
        with self.assertRaises(ValueError):
            add_dataset(
                self.db,
                dataset,
                database_type=database_type,
                metadata_database_type="type_that_does_not_exist",
                dataset_path=dataset_path,
                metadata_path=metadata_path,
            )

    @unittest.skipIf(
        ENV_S3_INTEGRATION not in os.environ
        and os.getenv(ENV_S3_INTEGRATION, "0").lower() in FALSE_VALUES,
        f"""Not an S3 integration test: {ENV_S3_INTEGRATION}
            environment variable not set to True.""",
    )
    def test_add_s3_dataset(self) -> None:  # pylint: disable=R0914
        """Test adding a dataset stored on S3."""
        dataset = "TINTIN_S3_TEST"
        database_type = PrivateDatabaseType.S3
        metadata_database_type = PrivateDatabaseType.S3
        bucket = "example"
        endpoint_url = "http://localhost:9000"
        access_key_id = "admin"
        secret_access_key = "admin123"
        credentials_name = "local_minio"
        key_file = "data/test_penguin.csv"
        key_metadata = "metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            bucket=bucket,
            key=key_file,
            endpoint_url=endpoint_url,
            credentials_name=credentials_name,
            metadata_bucket=bucket,
            metadata_key=key_metadata,
            metadata_endpoint_url=endpoint_url,
            metadata_access_key_id=access_key_id,
            metadata_secret_access_key=secret_access_key,
            metadata_credentials_name=credentials_name,
        )

        # Check dataset collection
        expected_dataset = {
            "dataset_name": dataset,
            "dataset_access": {
                "database_type": database_type,
                "bucket": bucket,
                "key": key_file,
                "endpoint_url": endpoint_url,
                "credentials_name": credentials_name,
            },
            "metadata_access": {
                "database_type": metadata_database_type,
                "bucket": bucket,
                "key": key_metadata,
                "endpoint_url": endpoint_url,
                "credentials_name": credentials_name,
            },
        }
        expected_dataset = DSInfo.model_validate(expected_dataset).model_dump()

        dataset_found = self.db.datasets.find_one({"dataset_name": dataset})
        del dataset_found["_id"]
        self.assertEqual(dataset_found, expected_dataset)

        # Check metadata collection
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        response = s3_client.get_object(Bucket=bucket, Key=key_metadata)
        expected_metadata = yaml.safe_load(response["Body"])
        expected_metadata = Metadata.model_validate(expected_metadata).model_dump()

        metadata_found = self.db.metadata.find_one({dataset: {"$exists": True}})[
            dataset
        ]
        self.assertEqual(metadata_found, expected_metadata)

    def test_add_datasets_via_yaml(self) -> None:
        """Test add datasets via a YAML file."""
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
        clean = False
        overwrite_datasets = False
        overwrite_metadata = False

        add_datasets_via_yaml(
            self.db, path, clean, overwrite_datasets, overwrite_metadata
        )

        verify_datasets()

        # Check clean works

        # Add new dataset and then add_datasets_via_yaml with clean option
        self.db.datasets.insert_one({"dataset_name": "Les aventures de Tintin"})

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

        # Check no clean and overwrite metadata
        add_datasets_via_yaml(
            self.db,
            path,
            clean=False,
            overwrite_datasets=True,
            overwrite_metadata=True,
        )
        verify_datasets()

    @unittest.skipIf(
        ENV_S3_INTEGRATION not in os.environ
        and os.getenv(ENV_S3_INTEGRATION, "0").lower() in FALSE_VALUES,
        f"""Not an S3 integration test: {ENV_S3_INTEGRATION}
            environment variable not set to True.""",
    )
    def test_add_s3_datasets_via_yaml(self) -> None:
        """Test add datasets via a YAML file."""
        # Load reference data
        dataset_path = "./tests/test_data/test_datasets_with_s3.yaml"
        with open(
            dataset_path,
            encoding="utf-8",
        ) as f:
            datasets = yaml.safe_load(f)
            tintin = DSInfo.model_validate(datasets["datasets"][3]).model_dump()

        with open(
            "./tests/test_data/metadata/penguin_metadata.yaml",
            encoding="utf-8",
        ) as f:
            tintin_metadata = yaml.safe_load(f)

        clean = False
        overwrite_datasets = False
        overwrite_metadata = False

        add_datasets_via_yaml(
            self.db,
            dataset_path,
            clean,
            overwrite_datasets,
            overwrite_metadata,
        )

        tintin_found = self.db.datasets.find_one({"dataset_name": "TINTIN_S3_TEST"})
        del tintin_found["_id"]
        print(tintin_found)
        print(tintin)
        self.assertEqual(tintin_found, tintin)

        metadata_found = self.db.metadata.find_one(
            {"TINTIN_S3_TEST": {"$exists": True}}
        )["TINTIN_S3_TEST"]
        self.assertEqual(metadata_found, tintin_metadata)

    def test_del_dataset(self) -> None:
        """Test dataset deletion."""
        # Setup: add one dataset
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )

        # Verify delete works
        del_dataset(self.db, dataset)

        dataset_found = self.db.datasets.find_one({"dataset_name": "PENGUIN"})
        self.assertEqual(dataset_found, None)

        nb_metadata = self.db.metadata.count_documents({})
        self.assertEqual(nb_metadata, 0)

        # Delete non-existing dataset should trigger decorator error
        with self.assertRaises(ValueError):
            del_dataset(self.db, dataset)

        # Delete dataset with non-existing metadata should trigger decorator error
        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )
        self.db.metadata.delete_many({dataset: {"$exists": True}})
        with self.assertRaises(ValueError):
            del_dataset(self.db, dataset)

    def test_get_dataset(self) -> None:
        """Test show dataset."""
        with self.assertRaises(ValueError):
            dataset_found = get_dataset(self.db, "PENGUIN")

        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )
        dataset_found = get_dataset(self.db, "PENGUIN")
        expected_dataset = {
            "dataset_name": dataset,
            "dataset_access": {"database_type": database_type, "path": dataset_path},
            "metadata_access": {
                "database_type": metadata_database_type,
                "path": metadata_path,
            },
        }
        expected_dataset = DSInfo.model_validate(expected_dataset).model_dump()
        self.assertEqual(dataset_found, expected_dataset)

    def test_get_metadata_of_dataset(self) -> None:
        """Test show metadata_dataset."""
        with self.assertRaises(ValueError):
            metadata_found = get_metadata_of_dataset(self.db, "PENGUIN")

        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )
        metadata_found = get_metadata_of_dataset(self.db, "PENGUIN")
        with open(metadata_path, encoding="utf-8") as f:
            expected_metadata = yaml.safe_load(f)
            expected_metadata = Metadata.model_validate(expected_metadata).model_dump()
        self.assertEqual(metadata_found, expected_metadata)

    def test_get_list_of_datasets(self) -> None:
        """Test get list of datasets."""
        list_datasets = get_list_of_datasets(self.db)
        self.assertEqual(list_datasets, [])

        path = "./tests/test_data/test_datasets.yaml"
        clean = False
        overwrite_datasets = False
        overwrite_metadata = False

        add_datasets_via_yaml(
            self.db, path, clean, overwrite_datasets, overwrite_metadata
        )
        list_datasets = get_list_of_datasets(self.db)
        self.assertEqual(list_datasets, ["PENGUIN", "IRIS", "BIRTHDAYS", "PUMS"])

    def test_drop_collection(self) -> None:
        """Test drop collection from db."""
        # Setup: add one dataset
        dataset = "PENGUIN"
        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = "./tests/test_data/metadata/penguin_metadata.yaml"

        add_dataset(
            self.db,
            dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )

        # Test
        collection = "datasets"
        drop_collection(self.db, collection)

        nb_datasets = self.db.datasets.count_documents({})
        self.assertEqual(nb_datasets, 0)

    def test_get_collection(self) -> None:
        """Test show collection from db."""
        dataset_collection = get_collection(self.db, "datasets")
        self.assertEqual(dataset_collection, [])

        path = "./tests/test_data/test_datasets.yaml"
        clean = False
        overwrite_datasets = False
        overwrite_metadata = False
        add_datasets_via_yaml(
            self.db, path, clean, overwrite_datasets, overwrite_metadata
        )
        with open(path, encoding="utf-8") as f:
            expected_dataset_collection = yaml.safe_load(f)
        dataset_collection = get_collection(self.db, "datasets")
        self.assertEqual(expected_dataset_collection["datasets"], dataset_collection)

    def test_add_demo_data_to_mongodb_admin(self) -> None:
        """Test add demo data to admin db."""

        if os.getenv(ENV_S3_INTEGRATION, "0").lower() in TRUE_VALUES:
            dataset_yaml = "tests/test_data/test_datasets_with_s3.yaml"
        else:
            dataset_yaml = "tests/test_data/test_datasets.yaml"

        add_demo_data_to_mongodb_admin(
            user_yaml="./tests/test_data/test_user_collection.yaml",
            dataset_yaml=dataset_yaml,
        )

        users_list = get_list_of_users(self.db)
        self.assertEqual(
            users_list, ["Dr. Antartica", "Tintin", "Milou", "BirthdayGirl"]
        )

        list_datasets = get_list_of_datasets(self.db)

        if os.getenv(ENV_S3_INTEGRATION, "0").lower() in TRUE_VALUES:
            self.assertEqual(
                list_datasets,
                ["PENGUIN", "IRIS", "PUMS", "TINTIN_S3_TEST", "BIRTHDAYS"],
            )
        else:
            self.assertEqual(list_datasets, ["PENGUIN", "IRIS", "BIRTHDAYS", "PUMS"])
