import argparse
from typing import Callable

import boto3
import yaml
from admin_database.utils import get_mongodb_url
from constants import PrivateDatabaseType
from pymongo import MongoClient
from pymongo.database import Database
from utils.error_handler import InternalServerException


def connect(
    function: Callable[[Database, argparse.Namespace], None]
) -> Callable:
    """Connect to the database"""

    def wrap_function(*args: argparse.Namespace) -> None:
        db_url: str = get_mongodb_url(args[0])
        db: Database = MongoClient(db_url)[args[0].db_name]
        return function(db, *args)

    return wrap_function


##########################  USERS  ########################## # noqa: E266
@connect
def add_user(db: Database, args: argparse.Namespace) -> None:
    """
    Add new user in users collection with initial values for all fields
    set by default.
    """
    if db.users.count_documents({"user_name": args.user}) > 0:
        raise ValueError("Cannot add user because already exists.")

    db.users.insert_one(
        {
            "user_name": args.user,
            "may_query": True,
            "datasets_list": [],
        }
    )
    print(f"Added user {args.user}.")


@connect
def add_user_with_budget(db: Database, args: argparse.Namespace) -> None:
    """
    Add new user in users collection with initial values
    for all fields set by default.
    """
    if db.users.count_documents({"user_name": args.user}) > 0:
        raise ValueError("Cannot add user because already exists. ")

    db.users.insert_one(
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


@connect
def del_user(db: Database, args: argparse.Namespace) -> None:
    """
    Delete all related information for user from the users collection.
    """
    db.users.delete_many({"user_name": args.user})
    print(f"Deleted user {args.user}.")


@connect
def add_dataset_to_user(db: Database, args: argparse.Namespace) -> None:
    """
    Add dataset with initialized budget values to list of datasets
    that the user has access to.
    Will not add if already added (no error will be raised in that case).
    """
    if db.users.count_documents({"user_name": args.user}) == 0:
        raise ValueError("Cannot add dataset because user does not exist. ")

    db.users.update_one(
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


@connect
def del_dataset_to_user(db: Database, args: argparse.Namespace) -> None:
    """
    Remove if exists the dataset (and all related budget info)
    from list of datasets that user has access to.
    """
    db.users.update_one(
        {"user_name": args.user},
        {"$pull": {"datasets_list": {"dataset_name": {"$eq": args.dataset}}}},
    )
    print(f"Remove access to dataset {args.dataset} from user {args.user}.")


@connect
def set_budget_field(db: Database, args: argparse.Namespace) -> None:
    """
    Set (for some reason) a budget field to a given value
    if given user exists and has access to given dataset.
    """
    db.users.update_one(
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


@connect
def set_may_query(db: Database, args: argparse.Namespace) -> None:
    """
    Set (for some reason) the 'may query' field to a given value
    if given user exists.
    """
    db.users.update_one(
        {"user_name": args.user},
        {"$set": {"may_query": (args.value == "True")}},
    )
    print(f"Set user {args.user} may query to True.")


@connect
def show_user(db: Database, args: argparse.Namespace) -> None:
    """
    Show a user
    """
    user = list(db.users.find({"user_name": args.user}))[0]
    user.pop("_id", None)
    print(user)


@connect
def create_users_collection(db: Database, args: argparse.Namespace) -> None:
    """
    Add all users from yaml file to the user collection
    """
    if args.clean:
        # Collection created from scratch
        db.users.drop()
        print("Cleaning done. \n")

    # Load yaml data and insert it
    with open(args.path) as f:
        user_dict = yaml.safe_load(f)
        # Filter out duplicates
        new_users = []
        existing_users = []
        for user in user_dict["users"]:
            if not db.users.find_one({"user_name": user["user_name"]}):
                new_users.append(user)
            else:
                existing_users.append(user)

        # Overwrite values for existing user with values from yaml
        if args.overwrite:
            if existing_users != []:
                for user in existing_users:
                    filter = {"user_name": user["user_name"]}
                    update_operation = {"$set": user}
                    db.users.update_many(filter, update_operation)
                print("Existing users updated. ")

        if new_users != []:
            # Insert new users
            db.users.insert_many(new_users)
            print(f"Added user data from yaml at {args.path}.")
        else:
            print("No new users added, they already exist in the server")


###################  DATASET TO DATABASE  ################### # noqa: E266
@connect
def add_dataset(db: Database, args: argparse.Namespace) -> None:
    """
    Set a database type to a dataset in dataset collection.
    """
    if db.datasets.count_documents({"dataset_name": args.dataset}) > 0:
        raise ValueError("Cannot add database because already set. ")

    # Step 1: add dataset
    dataset = {
        "dataset_name": args.dataset,
        "database_type": args.database_type,
    }

    if args.database_type == "LOCAL_DB":
        dataset["dataset_path"] = args.dataset_path
    elif args.database_type == "REMOTE_HTTP_DB":
        dataset["dataset_url"] = args.dataset_url
    elif args.database_type == "S3_DB":
        dataset["s3_bucket"] = args.s3_bucket
        dataset["s3_key"] = args.s3_key
        dataset["endpoint_url"] = args.endpoint_url
        dataset["aws_access_key_id"] = args.aws_access_key_id
        dataset["aws_secret_access_key"] = args.aws_secret_access_key
    else:
        raise ValueError(f"Unknown database type {args.database_type}")
    db.datasets.insert_one(dataset)

    # Step 2: add metadata
    if args.metadata_database_type == "LOCAL_DB":
        # Store metadata from yaml to metadata collection
        with open(args.metadata_path) as f:
            metadata_dict = yaml.safe_load(f)

    elif args.metadata_database_type == "S3_DB":
        client = boto3.client(
            "s3",
            endpoint_url=args.metadata_endpoint_url,
            aws_access_key_id=args.metadata_aws_access_key_id,
            aws_secret_access_key=args.metadata_aws_secret_access_key,
        )
        response = client.get_object(
            Bucket=args.metadata_s3_bucket, Key=args.metadata_s3_key
        )
        try:
            metadata_dict = yaml.safe_load(response["Body"])
        except yaml.YAMLError as e:
            return e
    else:
        raise ValueError(
            f"Unknown database type {args.metadata_database_type}"
        )
    db.metadata.insert_one({args.dataset: metadata_dict})

    print(
        f"Added dataset {args.dataset} with database {args.database_type} "
        f"and associated metadata."
    )


@connect
def add_datasets(db: Database, args: argparse.Namespace) -> None:
    """
    Set all database types to datasets in dataset collection based
    on yaml file.
    """
    if args.clean:
        # Collection created from scratch
        db.datasets.drop()
        db.metadata.drop()
        print("Cleaning done. \n")

    with open(args.path) as f:
        dataset_dict = yaml.safe_load(f)

    def verify_keys(d: dict, field: str, metadata: bool = False) -> None:
        if metadata:
            assert (
                field in d["metadata"].keys()
            ), f"Metadata of {d['dataset_name']} requires '{field}' key."
        else:
            assert (
                field in d.keys()
            ), f"Dataset {d['dataset_name']} requires '{field}' key."

    # Step 1: add datasets
    new_datasets = []
    existing_datasets = []
    for d in dataset_dict["datasets"]:
        verify_keys(d, "dataset_name")
        verify_keys(d, "database_type")
        verify_keys(d, "metadata")

        match d["database_type"]:
            case PrivateDatabaseType.REMOTE_HTTP:
                verify_keys(d, "dataset_url")
            case PrivateDatabaseType.S3:
                verify_keys(d, "s3_bucket")
                verify_keys(d, "s3_key")
            case PrivateDatabaseType.LOCAL:
                verify_keys(d, "dataset_path")
            case _:
                raise InternalServerException(
                    f"Unknown PrivateDatabaseType: {d['database_type']}"
                )

        # Fill datasets_list
        if not db.datasets.find_one({"dataset_name": d["dataset_name"]}):
            new_datasets.append(d)
        else:
            existing_datasets.append(d)

    # Overwrite values for existing dataset with values from yaml
    if args.overwrite_datasets:
        if existing_datasets != []:
            for d in existing_datasets:
                filter = {"dataset_name": d["dataset_name"]}
                update_operation = {"$set": d}
                db.datasets.update_many(filter, update_operation)
            print(
                f"Existing datasets updated with values"
                f"from yaml at {args.path}. "
            )

    # Add dataset collection
    if new_datasets != []:
        db.datasets.insert_many(new_datasets)
        print(f"Added datasets collection from yaml at {args.path}. ")

    # Step 2: add metadata collections (one metadata per dataset)
    for d in dataset_dict["datasets"]:
        dataset_name = d["dataset_name"]
        metadata_db_type = d["metadata"]["database_type"]

        verify_keys(d, "database_type", metadata=True)
        match metadata_db_type:
            case PrivateDatabaseType.LOCAL:
                verify_keys(d, "metadata_path", metadata=True)

                with open(d["metadata"]["metadata_path"]) as f:
                    metadata_dict = yaml.safe_load(f)

            case PrivateDatabaseType.S3:
                verify_keys(d, "s3_bucket", metadata=True)
                verify_keys(d, "s3_key", metadata=True)
                verify_keys(d, "endpoint_url", metadata=True)
                verify_keys(d, "aws_access_key_id", metadata=True)
                verify_keys(d, "aws_secret_access_key", metadata=True)
                client = boto3.client(
                    "s3",
                    endpoint_url=d["metadata"]["endpoint_url"],
                    aws_access_key_id=d["metadata"]["aws_access_key_id"],
                    aws_secret_access_key=d["metadata"][
                        "aws_secret_access_key"
                    ],
                )
                response = client.get_object(
                    Bucket=d["metadata"]["s3_bucket"],
                    Key=d["metadata"]["s3_key"],
                )
                try:
                    metadata_dict = yaml.safe_load(response["Body"])
                except yaml.YAMLError as e:
                    return e

            case _:
                raise InternalServerException(
                    "Unknown metadata_db_type PrivateDatabaseType:"
                    + f"{metadata_db_type}"
                )

        # Overwrite or not depending on config if metadata already exists
        filter = {dataset_name: metadata_dict}
        metadata = db.metadata.find_one(filter)

        if metadata and args.overwrite_metadata:
            print(f"Metadata updated for dataset : {dataset_name}.")
            db.metadata.update_one(
                filter, {"$set": {dataset_name: metadata_dict}}
            )
        elif metadata:
            print(
                "Metadata already exist. "
                "Use the command -om to overwrite with new values."
            )
        else:
            db.metadata.insert_one({dataset_name: metadata_dict})
            print(f"Added metadata of {dataset_name} dataset. ")


@connect
def del_dataset(db: Database, args: argparse.Namespace) -> None:
    """
    Delete dataset from dataset collection.
    """
    db.users.delete_many({"dataset_name": args.dataset_name})
    print(f"Deleted dataset {args.dataset_name}.")


#######################  COLLECTIONS  ####################### # noqa: E266
@connect
def drop_collection(db: Database, args: argparse.Namespace) -> None:
    """
    Delete collection.
    """
    eval(f"db.{args.collection}.drop()")
    print(f"Deleted collection {args.collection}.")


@connect
def show_collection(db: Database, args: argparse.Namespace) -> None:
    """
    Show a collection
    """
    collection_query = db[args.collection].find({})
    collections = []
    for document in collection_query:
        document.pop("_id", None)
        collections.append(document)
    print(collections)


if __name__ == "__main__":
    ########################################################################
    ########################## MongoDB Connection ############# # noqa: E266
    ########################################################################
    connection_parser = argparse.ArgumentParser(add_help=False)
    connection_parser.add_argument("-db_u", "--username", default="user")
    connection_parser.add_argument("-db_pwd", "--password", default="user_pwd")
    connection_parser.add_argument("-db_a", "--address", default="mongodb")
    connection_parser.add_argument("-db_p", "--port", default=27017)
    connection_parser.add_argument("-db_n", "--db_name", default="defaultdb")

    ########################################################################
    ######################## MongoDB Administration ############ # noqa: E266
    ########################################################################
    parser = argparse.ArgumentParser(
        description="MongoDB administration script for the database"
    )
    subparsers = parser.add_subparsers(
        title="subcommands", help="user database administration operations"
    )

    ##########################  USERS  ########################## # noqa: E266
    # Create the parser for the "add_user" command
    add_user_parser = subparsers.add_parser(
        "add_user",
        help="add user to users collection",
        parents=[connection_parser],
    )
    add_user_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_parser.set_defaults(func=add_user)

    # Create the parser for the "add_user_with_budget" command
    add_user_wb_parser = subparsers.add_parser(
        "add_user_with_budget",
        help="add user with budget to users collection",
        parents=[connection_parser],
    )
    add_user_wb_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_wb_parser.add_argument("-d", "--dataset", required=True, type=str)
    add_user_wb_parser.add_argument(
        "-e", "--epsilon", required=True, type=float
    )
    add_user_wb_parser.add_argument(
        "-del", "--delta", required=True, type=float
    )
    add_user_wb_parser.set_defaults(func=add_user_with_budget)

    # Create the parser for the "del_user" command
    del_user_parser = subparsers.add_parser(
        "del_user",
        help="delete user from users collection",
        parents=[connection_parser],
    )
    del_user_parser.add_argument("-u", "--user", required=True, type=str)
    del_user_parser.set_defaults(func=del_user)

    # Create the parser for the "add_dataset" command
    add_dataset_to_user_parser = subparsers.add_parser(
        "add_dataset_to_user",
        help="add dataset with initialized budget values for a user",
        parents=[connection_parser],
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
    add_dataset_to_user_parser.set_defaults(func=add_dataset_to_user)

    # Create the parser for the "del_dataset" command
    del_dataset_to_user_parser = subparsers.add_parser(
        "del_dataset_to_user",
        help="delete dataset for user in users collection",
        parents=[connection_parser],
    )
    del_dataset_to_user_parser.add_argument(
        "-u", "--user", required=True, type=str
    )
    del_dataset_to_user_parser.add_argument(
        "-d", "--dataset", required=True, type=str
    )
    del_dataset_to_user_parser.set_defaults(func=del_dataset_to_user)

    # Create the parser for the "set_budget_field" command
    set_budget_field_parser = subparsers.add_parser(
        "set_budget_field",
        help="set budget field to given value for given user and dataset",
        parents=[connection_parser],
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
    set_budget_field_parser.set_defaults(func=set_budget_field)

    # Create the parser for the "set_may_query" command
    set_may_query_parser = subparsers.add_parser(
        "set_may_query",
        help="set may query field to given value for given user",
        parents=[connection_parser],
    )
    set_may_query_parser.add_argument("-u", "--user", required=True, type=str)
    set_may_query_parser.add_argument(
        "-v", "--value", required=True, choices=["False", "True"]
    )
    set_may_query_parser.set_defaults(func=set_may_query)

    # Show the user
    show_user_parser = subparsers.add_parser(
        "show_user",
        help="show all metadata of user",
        parents=[connection_parser],
    )
    show_user_parser.add_argument("-u", "--user", required=True, type=str)
    show_user_parser.set_defaults(func=show_user)

    # Create the parser for the "create_example_users" command
    users_collection_from_yaml_parser = subparsers.add_parser(
        "create_users_collection",
        help="create users collection from yaml file",
        parents=[connection_parser],
    )
    users_collection_from_yaml_parser.add_argument(
        "-c",
        "--clean",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    users_collection_from_yaml_parser.add_argument(
        "-o",
        "--overwrite",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    users_collection_from_yaml_parser.add_argument(
        "-p", "--path", required=True, type=str
    )
    users_collection_from_yaml_parser.set_defaults(
        func=create_users_collection
    )

    #######################  ADD DATASETS  ####################### # noqa: E266
    # Create parser for dataset private database
    add_dataset_parser = subparsers.add_parser(
        "add_dataset",
        help="set in which database the dataset is stored",
        parents=[connection_parser],
    )
    # Dataset location
    add_dataset_parser.add_argument("-d", "--dataset", required=True)
    add_dataset_parser.add_argument("-db", "--database_type", required=True)
    add_dataset_parser.add_argument("-db_url", "--dataset_url", required=False)
    add_dataset_parser.add_argument("-s3b", "--s3_bucket", required=False)
    add_dataset_parser.add_argument("-s3k", "--s3_key", required=False)
    add_dataset_parser.add_argument(
        "-s3_url", "--endpoint_url", required=False
    )
    add_dataset_parser.add_argument(
        "-s3_ak", "--aws_access_key_id", required=False
    )
    add_dataset_parser.add_argument(
        "-s3_sak", "--aws_secret_access_key", required=False
    )
    # Metadata location
    add_dataset_parser.add_argument(
        "-m_db", "--metadata_database_type", required=True
    )
    add_dataset_parser.add_argument("-mp", "--metadata_path", required=False)
    add_dataset_parser.add_argument(
        "-m_s3b", "--metadata_s3_bucket", required=False
    )
    add_dataset_parser.add_argument(
        "-m_s3k", "--metadata_s3_key", required=False
    )
    add_dataset_parser.add_argument(
        "-m_s3_url", "--metadata_endpoint_url", required=False
    )
    add_dataset_parser.add_argument(
        "-m_s3_ak", "--metadata_aws_access_key_id", required=False
    )
    add_dataset_parser.add_argument(
        "-m_s3_sak", "--metadata_aws_secret_access_key", required=False
    )
    add_dataset_parser.set_defaults(func=add_dataset)

    # Create the parser for the "add_datasets" command
    add_datasets_parser = subparsers.add_parser(
        "add_datasets",
        help="create dataset to database type collection",
        parents=[connection_parser],
    )
    add_datasets_parser.add_argument("-p", "--path", required=True, type=str)
    add_datasets_parser.add_argument(
        "-c",
        "--clean",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_parser.add_argument(
        "-od",
        "--overwrite_datasets",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_parser.add_argument(
        "-om",
        "--overwrite_metadata",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_parser.set_defaults(func=add_datasets)

    #######################  COLLECTIONS  ####################### # noqa: E266
    # Create the parser for the "drop_collection" command
    drop_collection_parser = subparsers.add_parser(
        "drop_collection",
        help="delete collection from database",
        parents=[connection_parser],
    )
    drop_collection_parser.add_argument("-c", "--collection", required=True)
    drop_collection_parser.set_defaults(func=drop_collection)

    # Create the parser for the "show_users_collection" command
    show_collection_parser = subparsers.add_parser(
        "show_collection",
        help="print a collection",
        parents=[connection_parser],
    )
    show_collection_parser.add_argument("-c", "--collection", required=True)
    show_collection_parser.set_defaults(func=show_collection)

    args = parser.parse_args()
    args.func(args)
