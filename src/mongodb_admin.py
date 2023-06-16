import argparse
import pymongo
import yaml
from utils.constants import (
    MONGODB_CONTAINER_NAME,
    MONGODB_PORT,
    DATABASE_NAME,
    EXISTING_DATASETS,
    DATASET_METADATA_PATHS,
    EPSILON_LIMIT,
    DELTA_LIMIT,
    EPSILON_INITIAL,
    DELTA_INITIAL,
)


class MongoDB_Admin:
    """
    Overall administration operations of the MongoDB database.
    """

    def __init__(self, connection_string: str):
        """
        Connect to DB
        """
        self.db = pymongo.MongoClient(connection_string)[DATABASE_NAME]

    def add_user(self, args):
        """
        Add new user in users collection with initial values for all fields set by default.
        """
        if self.db.users.count_documents({"user_name": args.user}) > 0:
            raise ValueError("Cannot add user because already exists. ")

        self.db.users.insert_one(
            {
                "user_name": args.user,
                "may_query": True,
                "datasets_list": [],
            }
        )

    def del_user(self, args):
        """
        Delete all related information for user from the users collection.
        """
        self.db.users.delete_many({"user_name": args.user})

    def add_dataset_to_user(self, args):
        """
        Add dataset with initialized budget values to list of datasets that user has access to.
        Will not add if already added (no error will be raised in that case).
        """
        if self.db.users.count_documents({"user_name": args.user}) == 0:
            raise ValueError(
                "Cannot add dataset because user does not exist. "
            )

        self.db.users.update_one(
            {
                "user_name": args.user,
                "datasets_list.dataset_name": {"$ne": args.dataset},
            },
            {
                "$push": {
                    "datasets_list": {
                        "dataset_name": args.dataset,
                        "max_epsilon": EPSILON_LIMIT,
                        "max_delta": DELTA_LIMIT,
                        "current_epsilon": EPSILON_INITIAL,
                        "current_delta": DELTA_INITIAL,
                    }
                }
            },
        )

    def del_dataset_to_user(self, args):
        """
        Remove if exists the dataset (and all related budget info) from list of datasets that user has access to.
        """
        self.db.users.update_one(
            {"user_name": args.user},
            {
                "$pull": {
                    "datasets_list": {"dataset_name": {"$eq": args.dataset}}
                }
            },
        )

    def set_budget_field(self, args):
        """
        Set (for some reason) a budget field to a given value if given user exists and has access to given dataset.
        """
        self.db.users.update_one(
            {
                "user_name": args.user,
                "datasets_list.dataset_name": args.dataset,
            },
            {"$set": {f"datasets_list.$.{args.field}": args.value}},
        )

    def set_may_query(self, args):
        """
        Set (for some reason) the 'may query' field to a given value if given user exists.
        """
        self.db.users.update_one(
            {"user_name": args.user},
            {"$set": {"may_query": (args.value == "True")}},
        )

    def add_metadata(self, args):
        """
        Load metadata yaml file into a dict and add it in the metadata collection
        with dataset name as key.
        """
        with open(DATASET_METADATA_PATHS[args.dataset]) as f:
            metadata_dict = yaml.safe_load(f)
            self.db.metadata.insert_one({args.dataset: metadata_dict})

    def del_metadata(self, args):
        """
        Delete metadata associated to dataset from the metadata collection.
        """
        self.db.metadata.delete_many({args.dataset: {"$exists": True}})

    def drop_collection(self, args):
        """
        Delete collection.
        """
        eval(f"self.db.{args.collection}.drop()")

    # For testing purposes
    def create_example_users_collection(self, args):
        """
        Create example of users collection.
        """
        self.db.users.drop()  # To ensure the collection is created from scratch each time the method is called
        self.db.users.insert_many(
            [
                {
                    "user_name": "Alice",
                    "may_query": True,
                    "datasets_list": [
                        {
                            "dataset_name": "IRIS",
                            "max_epsilon": EPSILON_LIMIT,
                            "max_delta": DELTA_LIMIT,
                            "current_epsilon": EPSILON_INITIAL,
                            "current_delta": DELTA_INITIAL,
                        },
                        {
                            "dataset_name": "PENGUIN",
                            "max_epsilon": EPSILON_LIMIT,
                            "max_delta": DELTA_LIMIT,
                            "current_epsilon": EPSILON_INITIAL,
                            "current_delta": DELTA_INITIAL,
                        },
                    ],
                },
                {
                    "user_name": "Bob",
                    "may_query": True,
                    "datasets_list": [
                        {
                            "dataset_name": "IRIS",
                            "max_epsilon": EPSILON_LIMIT,
                            "max_delta": DELTA_LIMIT,
                            "current_epsilon": EPSILON_INITIAL,
                            "current_delta": DELTA_INITIAL,
                        }
                    ],
                },
            ]
        )


if __name__ == "__main__":
    admin = MongoDB_Admin(
        f"mongodb://{MONGODB_CONTAINER_NAME}:{MONGODB_PORT}/"
    )

    parser = argparse.ArgumentParser(
        prog="MongoDB administration script for the SDD POC Server"
    )
    subparsers = parser.add_subparsers(
        title="subcommands", help="database administration operations"
    )

    # Create the parser for the "add_user" command
    add_user_parser = subparsers.add_parser(
        "add_user", help="add user to users collection"
    )
    add_user_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_parser.set_defaults(func=admin.add_user)

    # Create the parser for the "del_user" command
    del_user_parser = subparsers.add_parser(
        "del_user", help="delete user from users collection"
    )
    del_user_parser.add_argument("-u", "--user", required=True, type=str)
    del_user_parser.set_defaults(func=admin.del_user)

    # Create the parser for the "add_dataset" command
    add_dataset_to_user_parser = subparsers.add_parser(
        "add_dataset_to_user",
        help="add dataset with initialized budget values for a user in users collection",
    )
    add_dataset_to_user_parser.add_argument(
        "-u", "--user", required=True, type=str
    )
    add_dataset_to_user_parser.add_argument(
        "-d", "--dataset", required=True, type=str
    )
    add_dataset_to_user_parser.set_defaults(func=admin.add_dataset_to_user)

    # Create the parser for the "del_dataset" command
    del_dataset_to_user_parser = subparsers.add_parser(
        "del_dataset_to_user",
        help="delete dataset for user in users collection",
    )
    del_dataset_to_user_parser.add_argument(
        "-u", "--user", required=True, type=str
    )
    del_dataset_to_user_parser.add_argument(
        "-d", "--dataset", required=True, type=str
    )
    del_dataset_to_user_parser.set_defaults(func=admin.del_dataset_to_user)

    # Create the parser for the "set_budget_field" command
    set_budget_field_parser = subparsers.add_parser(
        "set_budget_field",
        help="set budget field to given value for given user and dataset",
    )
    set_budget_field_parser.add_argument(
        "-u", "--user", required=True, type=str
    )
    set_budget_field_parser.add_argument(
        "-d", "--dataset", required=True, type=str
    )
    set_budget_field_parser.add_argument(
        "-f", "--field", required=True, choices=["max_epsilon", "max_delta"]
    )
    set_budget_field_parser.add_argument(
        "-v", "--value", required=True, type=float
    )
    set_budget_field_parser.set_defaults(func=admin.set_budget_field)

    # Create the parser for the "set_may_query" command
    set_may_query_parser = subparsers.add_parser(
        "set_may_query",
        help="set may query field to given value for given user",
    )
    set_may_query_parser.add_argument("-u", "--user", required=True, type=str)
    set_may_query_parser.add_argument(
        "-v", "--value", required=True, choices=["False", "True"]
    )
    set_may_query_parser.set_defaults(func=admin.set_may_query)

    # Create the parser for the "add_metadata" command
    add_metadata_parser = subparsers.add_parser(
        "add_metadata",
        help="add metadata for given dataset to metadata collection",
    )
    add_metadata_parser.add_argument(
        "-d", "--dataset", required=True, choices=EXISTING_DATASETS
    )
    add_metadata_parser.set_defaults(func=admin.add_metadata)

    # Create the parser for the "del_metadata" command
    del_metadata_parser = subparsers.add_parser(
        "del_metadata", help="delete metadata to metadata collection"
    )
    del_metadata_parser.add_argument(
        "-d", "--dataset", required=True, choices=EXISTING_DATASETS
    )
    del_metadata_parser.set_defaults(func=admin.del_metadata)

    # Create the parser for the "drop_collection" command
    drop_collection_parser = subparsers.add_parser(
        "drop_collection", help="delete collection from database"
    )
    drop_collection_parser.add_argument("-c", "--collection", required=True)
    drop_collection_parser.set_defaults(func=admin.drop_collection)

    # Create the parser for the "create_example_users" command (for testing purposes)
    create_example_users_parser = subparsers.add_parser(
        "create_ex_users", help="create example of users collection"
    )
    create_example_users_parser.set_defaults(
        func=admin.create_example_users_collection
    )

    args = parser.parse_args()
    args.func(args)
