import argparse
import pymongo
import yaml
from database.utils import get_mongodb_url
from utils.constants import (
    EXISTING_DATASETS,
    DATASET_METADATA_PATHS,
    DATABASE_NAME,
    EPSILON_LIMIT,
    DELTA_LIMIT,
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
        Add new user in users collection with initial values for
        all fields set by default.
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
        print(f"Added user {args.user}.")
    
    def add_user_with_budget(self, args):
        """
        Add new user in users collection with initial values for all fields set by default.
        """
        if self.db.users.count_documents({"user_name": args.user}) > 0:
            raise ValueError("Cannot add user because already exists. ")

        self.db.users.insert_one(
            {
                "user_name": args.user,
                "may_query": True,
                "datasets_list": [{
                    "dataset_name": args.dataset,
                    "initial_epsilon": args.epsilon,
                    "initial_delta": args.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }],
            }
        )
        print(f"Added access to user {args.user} with dataset {args.dataset},"
                f" budget epsilon {args.epsilon} and delta {args.delta}.")

    def del_user(self, args):
        """
        Delete all related information for user from the users collection.
        """
        self.db.users.delete_many({"user_name": args.user})
        print(f"Deleted user {args.user}.")

    def add_dataset_to_user(self, args):
        """
        Add dataset with initialized budget values to list of datasets that
        user has access to.
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
                        "initial_epsilon": args.epsilon,
                        "initial_delta": args.delta,
                        "total_spent_epsilon": 0.0,
                        "total_spent_delta": 0.0,
                    }
                }
            },
        )
        print(f"Added access to dataset {args.dataset} to user {args.user}"
                f" with budget epsilon {args.epsilon} and delta {args.delta}.")

    def del_dataset_to_user(self, args):
        """
        Remove if exists the dataset (and all related budget info) from list
        of datasets that user has access to.
        """
        self.db.users.update_one(
            {"user_name": args.user},
            {
                "$pull": {
                    "datasets_list": {"dataset_name": {"$eq": args.dataset}}
                }
            },
        )
        print(f"Remove access to dataset {args.dataset} from user {args.user}.")

    def set_budget_field(self, args):
        """
        Set (for some reason) a budget field to a given value if given
        user exists and has access to given dataset.
        """
        self.db.users.update_one(
            {
                "user_name": args.user,
                "datasets_list.dataset_name": args.dataset,
            },
            {"$set": {f"datasets_list.$.{args.field}": args.value}},
        )
        print(f"Set budget of {args.user} for dataset {args.dataset}"
                f" of {args.field} to {args.value}.")

    def set_may_query(self, args):
        """
        Set (for some reason) the 'may query' field to a given value if
        given user exists.
        """
        self.db.users.update_one(
            {"user_name": args.user},
            {"$set": {"may_query": (args.value == "True")}},
        )
        print(f"Set user {args.user} may query.")

    def show_user(self, args):
        """
        Show a user
        """
        print(list(self.db.users.find({"user_name": args.user})))

    def add_metadata(self, args):
        """
        Load metadata yaml file into a dict and add it in the metadata
        collection with dataset name as key.
        """
        with open(args.metadata_path) as f:
            metadata_dict = yaml.safe_load(f)
            # Make sure to remove old versions
            self.db.metadata.delete_many({args.dataset: {"$exists": True}})
            self.db.metadata.insert_one({args.dataset: metadata_dict})
        print(f"Added metadata of {args.dataset} dataset.")

    def del_metadata(self, args):
        """
        Delete metadata associated to dataset from the metadata collection.
        """
        self.db.metadata.delete_many({args.dataset: {"$exists": True}})
        print(f"Deleted metadata of {args.dataset} dataset.")

    def drop_collection(self, args):
        """
        Delete collection.
        """
        eval(f"self.db.{args.collection}.drop()")
        print(f"Deleted collection {args.collection}.")
    
    def show_collection(self, args):
        """
        Show a collection
        """
        collection_query = self.db[args.collection].find({})
        collections = []
        for document in collection_query:
            document.pop('_id', None)
            collections.append(document)
        print(collections)

    # For testing purposes
    def create_example_users_collection(self):
        """
        Create example of users collection.
        """
        # To ensure the collection is created from scratch
        self.db.users.drop()
        self.db.users.insert_many(
            [
                {
                    "user_name": "Antartica",
                    "may_query": True,
                    "datasets_list": [
                        {
                            "dataset_name": "IRIS",
                            "initial_epsilon": EPSILON_LIMIT,
                            "initial_delta": DELTA_LIMIT,
                            "total_spent_epsilon": 0.0,
                            "total_spent_delta": 0.0,
                        },
                        {
                            "dataset_name": "PENGUIN",
                            "initial_epsilon": EPSILON_LIMIT,
                            "initial_delta": DELTA_LIMIT,
                            "total_spent_epsilon": 0.0,
                            "total_spent_delta": 0.0,
                        },
                    ],
                },
                {
                    "user_name": "Bob",
                    "may_query": True,
                    "datasets_list": [
                        {
                            "dataset_name": "IRIS",
                            "initial_epsilon": EPSILON_LIMIT,
                            "initial_delta": DELTA_LIMIT,
                            "total_spent_epsilon": 0.0,
                            "total_spent_delta": 0.0,
                        }
                    ],
                },
            ]
        )


if __name__ == "__main__":
    # Get url with vault credentials
    db_url = get_mongodb_url()
    admin = MongoDB_Admin(db_url)

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

    # Create the parser for the "add_user_with_budget" command
    add_user_wb_parser = subparsers.add_parser(
        "add_user_with_budget", help="add user to users collection"
    )
    add_user_wb_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_wb_parser.add_argument("-d", "--dataset", required=True, type=str)
    add_user_wb_parser.add_argument("-e", "--epsilon", required=True, type=float)
    add_user_wb_parser.add_argument("-del", "--delta", required=True, type=float)
    add_user_wb_parser.set_defaults(func=admin.add_user_with_budget)

    # Create the parser for the "del_user" command
    del_user_parser = subparsers.add_parser(
        "del_user", help="delete user from users collection"
    )
    del_user_parser.add_argument("-u", "--user", required=True, type=str)
    del_user_parser.set_defaults(func=admin.del_user)

    # Create the parser for the "add_dataset" command
    add_dataset_to_user_parser = subparsers.add_parser(
        "add_dataset_to_user",
        help="add dataset with initialized budget values for a user",
    )
    add_dataset_to_user_parser.add_argument(
        "-u", "--user", required=True, type=str
    )
    add_dataset_to_user_parser.add_argument(
        "-d", "--dataset", required=True, type=str
    )
    add_dataset_to_user_parser.add_argument("-e", "--epsilon", required=True, type=float)
    add_dataset_to_user_parser.add_argument("-del", "--delta", required=True, type=float)
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
        "-f", "--field", required=True, choices=["initial_epsilon", "initial_delta"]
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

    # Show the user
    show_user_parser = subparsers.add_parser(
        "show_user",
        help="show all metadata of user",
    )
    show_user_parser.add_argument("-u", "--user", required=True, type=str)
    show_user_parser.set_defaults(func=admin.show_user)

    # Create the parser for the "add_metadata" command
    add_metadata_parser = subparsers.add_parser(
        "add_metadata",
        help="add metadata for given dataset to metadata collection",
    )
    add_metadata_parser.add_argument(
        "-d", "--dataset", required=True, choices=EXISTING_DATASETS
    )
    add_metadata_parser.add_argument(
        "-mp", "--metadata_path", required=True, type=str
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

    # Create the parser for the "show_users_collection" command
    show_collection_parser = subparsers.add_parser(
        "show_collection", help="print the users collection"
    )
    show_collection_parser.add_argument("-c", "--collection", default="users")
    show_collection_parser.set_defaults(
        func=admin.show_collection
    )

    # Create the parser for the "create_example_users" command (for testing purposes)
    create_example_users_parser = subparsers.add_parser(
        "create_ex_users", help="create example of users collection"
    )
    create_example_users_parser.set_defaults(
        func=admin.create_example_users_collection
    )

    args = parser.parse_args()
    args.func(args)
