import os
from pymongo import MongoClient
from pymongo.database import Database
from types import SimpleNamespace
import unittest

from admin_database.utils import get_mongodb_url
from mongodb_admin import (
    add_user,
    add_user_with_budget,
    del_user,
    add_dataset_to_user,
    del_dataset_to_user,
    set_budget_field,
    set_may_query,
    show_user,
    drop_collection,
    create_users_collection
)
from utils.config import Config, get_config, CONFIG_LOADER
from tests.constants import ENV_MONGO_INTEGRATION

@unittest.skipIf(not(bool(os.getenv(ENV_MONGO_INTEGRATION, False))), f"Not an MongoDB integration test: {ENV_MONGO_INTEGRATION} environment variable not set to True.")
class TestRootAPIEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(self) -> None:
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config_mongo.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml"
        )

        self.db_config: Config = get_config().admin_database
        db_url: str = get_mongodb_url(self.db_config)
        self.db: Database = MongoClient(db_url)[self.db_config.db_name]
    
    def setUp(self) -> None:
        self.args = SimpleNamespace(**vars(get_config().admin_database))

    def tearDown(self) -> None:
        self.args = SimpleNamespace(**vars(get_config().admin_database))
        
        self.args.collection = "metadata"
        drop_collection(self.args)

        self.args.collection = "datasets"
        drop_collection(self.args)

        self.args.collection = "users"
        drop_collection(self.args)

        self.args.collection = "queries_archives"
        drop_collection(self.args)

        self.args = None


    def test_add_user(self) -> None:
        self.args.user = "Tintin"
        
        # Add user
        add_user(self.args)

        expected_user = {
            "user_name": self.args.user,
            "may_query": True,
            "datasets_list": []
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Adding existing user raises error
        with self.assertRaises(ValueError):
            add_user(self.args)

    def test_add_user_wb(self) -> None:
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
                    "total_spent_delta": 0.0
                }
            ]
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Adding budget to existing user should raise error
        with self.assertRaises(ValueError):
            add_user_with_budget(self.args)

    def test_del_user(self) -> None:
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
                    "total_spent_delta": 0.0
                }
            ]
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
            "datasets_list": []
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
                    "total_spent_delta": 0.0
                }
            ]
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
                    "total_spent_delta": 0.0
                }
            ]
        }

        user_found = self.db.users.find_one({"user_name": "Tintin"})
        del user_found["_id"]

        self.assertEqual(user_found, expected_user)

        # Raises error when user does not exist
        self.args.user = "Milou"
        
        with self.assertRaises(ValueError):
            set_may_query(self.args)

    def test_create_users_collection(self) -> None:
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
                    "total_spent_delta": 0.0
                }
            ]
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
                    "total_spent_delta": 0.0
                }
            ]
        }

        user_found = self.db.users.find_one({"user_name": "Milou"})
        del user_found["_id"]

        self.assertEqual(user_found, milou)

        # Check cleaning
        self.args.user = "Tintin"
        self.args.field = "initial_epsilon"
        self.args.value = False
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



        

            




        