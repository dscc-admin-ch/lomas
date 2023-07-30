import argparse
import pymongo
import yaml
from utils.constants import (
    MONGODB_CONTAINER_NAME,
    MONGODB_PORT,
    ADMIN_DATABASE_NAME,
    CONSTANT_PATH_DB,
    S3_DB,
)


class MongoDB_Admin:
    """
    Overall administration operations of the MongoDB database.
    """

    def __init__(self, connection_string: str):
        """
        Connect to DB
        """
        self.db = pymongo.MongoClient(connection_string)[ADMIN_DATABASE_NAME]

    ##########################  USERS  ########################## # noqa: E266
    def add_user(self, args):
        """
        Add new user in users collection with initial values for all fields
        set by default.
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
        Add new user in users collection with initial values
        for all fields set by default.
        """
        if self.db.users.count_documents({"user_name": args.user}) > 0:
            raise ValueError("Cannot add user because already exists. ")

        self.db.users.insert_one(
            {
                "user_name": args.user,
                "may_query": True,
                "datasets_list": [
                    {
                        "dataset_name": args.dataset,
                        "initial_epsilon": args.epsilon,
                        "initial_delta": args.delta,
                        "total_spent_epsilon": 0.0,
                        "total_spent_delta": 0.0,
                    }
                ],
            }
        )
        print(
            f"Added access to user {args.user} with dataset {args.dataset},"
            f" budget epsilon {args.epsilon} and delta {args.delta}."
        )

    def del_user(self, args):
        """
        Delete all related information for user from the users collection.
        """
        self.db.users.delete_many({"user_name": args.user})
        print(f"Deleted user {args.user}.")

    def add_dataset_to_user(self, args):
        """
        Add dataset with initialized budget values to list of datasets
        that the user has access to.
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
        print(
            f"Added access to dataset {args.dataset} to user {args.user}"
            f" with budget epsilon {args.epsilon} and delta {args.delta}."
        )

    def del_dataset_to_user(self, args):
        """
        Remove if exists the dataset (and all related budget info)
        from list of datasets that user has access to.
        """
        self.db.users.update_one(
            {"user_name": args.user},
            {
                "$pull": {
                    "datasets_list": {"dataset_name": {"$eq": args.dataset}}
                }
            },
        )
        print(
            f"Remove access to dataset {args.dataset} from user {args.user}."
        )

    def set_budget_field(self, args):
        """
        Set (for some reason) a budget field to a given value
        if given user exists and has access to given dataset.
        """
        self.db.users.update_one(
            {
                "user_name": args.user,
                "datasets_list.dataset_name": args.dataset,
            },
            {"$set": {f"datasets_list.$.{args.field}": args.value}},
        )
        print(
            f"Set budget of {args.user} for dataset {args.dataset}"
            f" of {args.field} to {args.value}."
        )

    def set_may_query(self, args):
        """
        Set (for some reason) the 'may query' field to a given value
        if given user exists.
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

    def create_users_collection(self, args):
        """
        Add all users from yaml file to the user collection
        """

        # Ensure collection created from scratch each time the method is called
        self.db.users.drop()

        # Load yaml data and insert it
        with open(args.path) as f:
            user_dict = yaml.safe_load(f)
            self.db.users.insert_many(user_dict["users"])

        print(f"Added user data from yaml at {args.path}.")

    ###################  DATASET TO DATABASE  ################### # noqa: E266
    def add_dataset(self, args):
        """
        Set a database type to a dataset in dataset collection.
        """
        if (
            self.db.datasets.count_documents({"dataset_name": args.dataset})
            > 0
        ):
            raise ValueError("Cannot add database because already set. ")

        self.db.datasets.insert_one(
            {
                "dataset_name": args.dataset,
                "database_type": args.database_type,
                "metadata_path": args.metadata_path,
            }
        )

        # Store metadata from yaml to metadata collection
        with open(args.metadata_path) as f:
            metadata_dict = yaml.safe_load(f)
            self.db.metadata.insert_one({args.dataset: metadata_dict})

        print(
            f"Added dataset {args.dataset} with database {args.database_type} "
            f"and metadata from {args.metadata_path}."
        )

    def add_datasets(self, args):
        """
        Set all database types to datasets in dataset collection based
        on yaml file.
        """
        # Ensure collection created from scratch each time the method is called
        self.db.datasets.drop()
        self.db.metadata.drop()

        with open(args.path) as f:
            dataset_dict = yaml.safe_load(f)

        def verify_keys(d, field):
            assert (
                field in d.keys()
            ), f"Dataset {d['dataset_name']} requires '{field}' key."

        # Verify inputs
        for d in dataset_dict["datasets"]:
            verify_keys(d, "dataset_name")
            verify_keys(d, "dataset_type")
            verify_keys(d, "metadata_path")

            if d["database_type"] == CONSTANT_PATH_DB:
                verify_keys(d, "dataset_path")
            elif d["database_type"] == S3_DB:
                verify_keys(d, "bucket")
                verify_keys(d, "prefix")
            else:
                raise ValueError(f"Dataset type {d['database_type']} unknown")

        # Add dataset collecion
        self.db.datasets.insert_many(dataset_dict["datasets"])
        print(f"Added datasets collection from yaml at {args.path}. ")

        # Add metadata collection (one metadata per dataset)
        for d in dataset_dict["datasets"]:
            dataset_name = d["dataset_name"]
            with open(d["metadata_path"]) as f:
                metadata_dict = yaml.safe_load(f)
                self.db.metadata.insert_one({dataset_name: metadata_dict})
                print(f"Added metadata of {dataset_name} dataset. ")

    def del_dataset(self, args):
        """
        Delete dataset from dataset collection.
        """
        self.db.users.delete_many({"dataset_name": args.dataset_name})
        print(f"Deleted dataset {args.dataset_name}.")

    #######################  COLLECTIONS  ####################### # noqa: E266
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
            document.pop("_id", None)
            collections.append(document)
        print(collections)


if __name__ == "__main__":
    admin = MongoDB_Admin(
        f"mongodb://{MONGODB_CONTAINER_NAME}:{MONGODB_PORT}/"
    )

    parser = argparse.ArgumentParser(
        prog="MongoDB administration script for the user database"
    )
    subparsers = parser.add_subparsers(
        title="subcommands", help="user database administration operations"
    )

    ##########################  USERS  ########################## # noqa: E266
    # Create the parser for the "add_user" command
    add_user_parser = subparsers.add_parser(
        "add_user", help="add user to users collection"
    )
    add_user_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_parser.set_defaults(func=admin.add_user)

    # Create the parser for the "add_user_with_budget" command
    add_user_wb_parser = subparsers.add_parser(
        "add_user_with_budget", help="add user with budget to users collection"
    )
    add_user_wb_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_wb_parser.add_argument("-d", "--dataset", required=True, type=str)
    add_user_wb_parser.add_argument(
        "-e", "--epsilon", required=True, type=float
    )
    add_user_wb_parser.add_argument(
        "-del", "--delta", required=True, type=float
    )
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
    add_dataset_to_user_parser.add_argument(
        "-e", "--epsilon", required=True, type=float
    )
    add_dataset_to_user_parser.add_argument(
        "-del", "--delta", required=True, type=float
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
        "-f",
        "--field",
        required=True,
        choices=["initial_epsilon", "initial_delta"],
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

    # Create the parser for the "create_example_users" command
    users_collection_from_yaml_parser = subparsers.add_parser(
        "create_users_collection",
        help="create users collection from yaml file",
    )
    users_collection_from_yaml_parser.add_argument(
        "-p", "--path", required=True, type=str
    )
    users_collection_from_yaml_parser.set_defaults(
        func=admin.create_users_collection
    )

    #######################  ADD DATASETS  ####################### # noqa: E266
    # Create parser for dataset private database
    add_dataset_parser = subparsers.add_parser(
        "add_dataset",
        help="set in which database the dataset is stored",
    )
    add_dataset_parser.add_argument("-d", "--dataset", required=True)
    add_dataset_parser.add_argument("-db", "--database_type", required=True)
    add_dataset_parser.add_argument("-mp", "--metadata_path", required=True)
    add_dataset_parser.set_defaults(func=admin.add_dataset)

    # Create the parser for the "add_datasets" command
    add_datasets_parser = subparsers.add_parser(
        "add_datasets",
        help="create dataset to database type collection",
    )
    add_datasets_parser.add_argument("-p", "--path", required=True, type=str)
    add_datasets_parser.set_defaults(func=admin.add_datasets)

    #######################  COLLECTIONS  ####################### # noqa: E266
    # Create the parser for the "drop_collection" command
    drop_collection_parser = subparsers.add_parser(
        "drop_collection", help="delete collection from database"
    )
    drop_collection_parser.add_argument("-c", "--collection", required=True)
    drop_collection_parser.set_defaults(func=admin.drop_collection)

    # Create the parser fir the "show_users_collection" command
    show_collection_parser = subparsers.add_parser(
        "show_collection", help="print the users collection"
    )
    show_collection_parser.add_argument("-c", "--collection", default="users")
    show_collection_parser.set_defaults(func=admin.show_collection)

    args = parser.parse_args()
    args.func(args)
