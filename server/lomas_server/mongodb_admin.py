import argparse
import functools
from typing import Callable
from warnings import warn

import boto3
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import WriteConcernError
from pymongo.results import _WriteResult
import yaml

from admin_database.utils import get_mongodb_url
from constants import PrivateDatabaseType
from utils.error_handler import InternalServerException
from utils.loggr import LOG


def connect(
    function: Callable[[Database, argparse.Namespace], None]
) -> Callable:
    """Returns a wrapping function to connect to the database

    Args:
        function (Callable[[Database, argparse.Namespace], None]):
            Any function taking a Database instance as argument,
            as well as some argparse.Namespace object.

    Returns:
        Callable: The wrapping function which sets up the database
        connection before calling the wrapped function.
    """

    @functools.wraps(function)
    def wrap_function(*arguments: argparse.Namespace) -> None:
        db_url: str = get_mongodb_url(arguments[0])
        db: Database = MongoClient(db_url)[arguments[0].db_name]
        return function(db, *arguments)

    return wrap_function


def check_user_exists(enforce_true: bool) -> Callable:
    """Creates a wrapper function that raises a ValueError if the supplied
    user does (not) exist in the user collection depending on the
    enforce_true parameter.

    Args:
        enforce_true (bool): If set to True, the wrapper will enforce
            the user is already in the database. If set to False, it
            will enforce the user is NOT in the database.

    Returns:
        Callable: The wrapper function that enforces user presence
            (or absence) before calling the suplied function.
    """

    def inner_func(
        function: Callable[[Database, argparse.Namespace], None]
    ) -> Callable:
        @functools.wraps(function)
        def wrapper_decorator(*arguments: argparse.Namespace) -> None:
            db = arguments[0]
            user = arguments[1].user

            user_count = db.users.count_documents({"user_name": user})

            if enforce_true and user_count == 0:
                raise ValueError(
                    f"User {user} does not exist in user collecion"
                )
            if not enforce_true and user_count > 0:
                raise ValueError(
                    f"User {user} already exists in user collection"
                )

            return function(*arguments)  # type: ignore

        return wrapper_decorator

    return inner_func


def check_user_has_dataset(enforce_true: bool) -> Callable:
    """Creates a wrapper function that raises a ValueError if the supplied
    user has access (or not) to the supplied dataset depending on the
    enforce_true parameter.

    Args:
        enforce_true (bool): If set to true, the wrapper function will
            enforce the user has access to the dataset. If set to False,
            the wrapper function will enforce the user has NOT access
            to the specified dataset.

    Returns:
        Callable: The wrapper function that asserts user access (or not)
            to the provided dataset.
    """

    def inner_func(
        function: Callable[[Database, argparse.Namespace], None]
    ) -> Callable:
        @functools.wraps(function)
        def wrapper_decorator(*arguments: argparse.Namespace) -> None:
            db = arguments[0]
            user = arguments[1].user
            dataset = arguments[1].dataset

            user_and_ds_count = db.users.count_documents(
                {
                    "user_name": user,
                    "datasets_list": {"$elemMatch": {"dataset_name": dataset}},
                }
            )

            if enforce_true and user_and_ds_count == 0:
                raise ValueError(
                    f"User {user} does not have dataset {dataset}"
                )
            if not enforce_true and user_and_ds_count > 0:
                raise ValueError(f"User {user} already has dataset {dataset}")

            return function(*arguments)  # type: ignore

        return wrapper_decorator

    return inner_func


def check_dataset_and_metadata_exist(enforce_true: bool) -> Callable:
    """Creates a wrapper function that raises a ValueError
    if the supplied user does not already exist in the user collection.
    """

    def inner_func(
        function: Callable[[Database, argparse.Namespace], None]
    ) -> Callable:
        @functools.wraps(function)
        def wrapper_decorator(*arguments: argparse.Namespace) -> None:
            db = arguments[0]
            dataset = arguments[1].dataset

            dataset_count = db.datasets.count_documents(
                {"dataset_name": dataset}
            )

            if enforce_true and dataset_count == 0:
                raise ValueError(
                    f"Dataset {dataset} does not exist in dataset collecion"
                )
            if not enforce_true and dataset_count > 0:
                raise ValueError(
                    f"Dataset {dataset} already exists in dataset collection"
                )

            metadata_count = db.metadata.count_documents(
                {dataset: {"$exists": True}}
            )

            if enforce_true and metadata_count == 0:
                raise ValueError(
                    f"Metadata for dataset {dataset} does"
                    "not exist in metadata collecion"
                )
            if not enforce_true and metadata_count > 0:
                raise ValueError(
                    f"Metadata for dataset {dataset} already"
                    "exists in metadata collection"
                )

            return function(*arguments)  # type: ignore

        return wrapper_decorator

    return inner_func


def check_result_acknowledged(res: _WriteResult) -> None:
    """Raises an exception if the result is not acknowledged.

    Args:
        res (_WriteResult): The PyMongo WriteResult to check.

    Raises:
        Exception: If the result is not acknowledged.
    """
    if not res.acknowledged:
        raise WriteConcernError(
            "Write request not acknowledged by MongoDB database."
        )


##########################  USERS  ########################## # noqa: E266
@connect
@check_user_exists(False)
def add_user(db: Database, arguments: argparse.Namespace) -> None:
    """Add new user in users collection with initial values for all fields
    set by default.

    Args:
        db (Database): The database connection.
        arguments (argparse.Namespace):

    Raises:
        ValueError: If the user already exists.
        Exception: If the write result is not acknowledged.
    """

    res = db.users.insert_one(
        {
            "user_name": arguments.user,
            "may_query": True,
            "datasets_list": [],
        }
    )

    check_result_acknowledged(res)

    LOG.info(f"Added user {arguments.user}.")


@connect
@check_user_exists(False)
def add_user_with_budget(db: Database, arguments: argparse.Namespace) -> None:
    """Add new user in users collection with initial values
    for all fields set by default.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_

    Raises:
        ValueError: _description_
    """
    res = db.users.insert_one(
        {
            "user_name": arguments.user,
            "may_query": True,
            "datasets_list": [
                {
                    "dataset_name": arguments.dataset,
                    "initial_epsilon": arguments.epsilon,
                    "initial_delta": arguments.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            ],
        }
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Added access to user {arguments.user} "
        + f"with dataset {arguments.dataset}, "
        + f"budget epsilon {arguments.epsilon} and "
        + f"delta {arguments.delta}."
    )


@connect
@check_user_exists(True)
def del_user(db: Database, arguments: argparse.Namespace) -> None:
    """Delete all related information for user from the users collection.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    res = db.users.delete_many({"user_name": arguments.user})
    check_result_acknowledged(res)

    LOG.info(f"Deleted user {arguments.user}.")


@connect
@check_user_exists(True)
@check_user_has_dataset(False)
def add_dataset_to_user(db: Database, arguments: argparse.Namespace) -> None:
    """Add dataset with initialized budget values to list of datasets
    that the user has access to.
    Will not add if already added (no error will be raised in that case).

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_

    Raises:
        ValueError: _description_
    """
    res = db.users.update_one(
        {
            "user_name": arguments.user,
            "datasets_list.dataset_name": {"$ne": arguments.dataset},
        },
        {
            "$push": {
                "datasets_list": {
                    "dataset_name": arguments.dataset,
                    "initial_epsilon": arguments.epsilon,
                    "initial_delta": arguments.delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            }
        },
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Added access to dataset {arguments.dataset}"
        f"to user {arguments.user}"
        f" with budget epsilon {arguments.epsilon}"
        f" and delta {arguments.delta}."
    )


@connect
@check_user_exists(True)
@check_user_has_dataset(True)
def del_dataset_to_user(db: Database, arguments: argparse.Namespace) -> None:
    """Remove if exists the dataset (and all related budget info)
    from list of datasets that user has access to.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    res = db.users.update_one(
        {"user_name": arguments.user},
        {
            "$pull": {
                "datasets_list": {"dataset_name": {"$eq": arguments.dataset}}
            }
        },
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Remove access to dataset {arguments.dataset}"
        + f" from user {arguments.user}."
    )


@connect
@check_user_exists(True)
@check_user_has_dataset(True)
def set_budget_field(db: Database, arguments: argparse.Namespace) -> None:
    """Set (for some reason) a budget field to a given value
    if given user exists and has access to given dataset.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    res = db.users.update_one(
        {
            "user_name": arguments.user,
            "datasets_list.dataset_name": arguments.dataset,
        },
        {"$set": {f"datasets_list.$.{arguments.field}": arguments.value}},
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Set budget of {arguments.user} for dataset {arguments.dataset}"
        f" of {arguments.field} to {arguments.value}."
    )


@connect
@check_user_exists(True)
def set_may_query(db: Database, arguments: argparse.Namespace) -> None:
    """Set (for some reason) the 'may query' field to a given value
    if given user exists.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    res = db.users.update_one(
        {"user_name": arguments.user},
        {"$set": {"may_query": (arguments.value == "True")}},
    )

    check_result_acknowledged(res)

    LOG.info(f"Set user {arguments.user} may query to True.")


@connect
@check_user_exists(True)
def show_user(db: Database, arguments: argparse.Namespace) -> None:
    """Show a user

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    user = list(db.users.find({"user_name": arguments.user}))[0]
    user.pop("_id", None)
    LOG.info(user)


@connect
def create_users_collection(
    db: Database, arguments: argparse.Namespace
) -> None:
    """Add all users from yaml file to the user collection

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    if arguments.clean:
        # Collection created from scratch
        db.users.drop()
        LOG.info("Cleaning done. \n")

    # Load yaml data and insert it
    with open(arguments.path, encoding="utf-8") as f:
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
        if existing_users:
            if arguments.overwrite:
                for user in existing_users:
                    user_filter = {"user_name": user["user_name"]}
                    update_operation = {"$set": user}
                    res: _WriteResult = db.users.update_many(
                        user_filter, update_operation
                    )
                    check_result_acknowledged(res)
                LOG.info("Existing users updated. ")
            else:
                warn(
                    "Some users already present in database."
                    "Overwrite is set to False."
                )

        if new_users:
            # Insert new users
            res = db.users.insert_many(new_users)
            check_result_acknowledged(res)
            LOG.info(f"Added user data from yaml at {arguments.path}.")
        else:
            LOG.info("No new users added, they already exist in the server")


###################  DATASET TO DATABASE  ################### # noqa: E266
@connect
@check_dataset_and_metadata_exist(False)
def add_dataset(db: Database, arguments: argparse.Namespace) -> None:
    """Set a database type to a dataset in dataset collection.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    if db.datasets.count_documents({"dataset_name": arguments.dataset}) > 0:
        raise ValueError("Cannot add database because already set. ")

    # Step 1: Build dataset
    dataset = {
        "dataset_name": arguments.dataset,
        "database_type": arguments.database_type,
    }

    if arguments.database_type == PrivateDatabaseType.PATH:
        dataset["dataset_path"] = arguments.dataset_path
    elif arguments.database_type == PrivateDatabaseType.S3:
        dataset["s3_bucket"] = arguments.s3_bucket
        dataset["s3_key"] = arguments.s3_key
        dataset["endpoint_url"] = arguments.endpoint_url
        dataset["aws_access_key_id"] = arguments.aws_access_key_id
        dataset["aws_secret_access_key"] = arguments.aws_secret_access_key
    else:
        raise ValueError(f"Unknown database type {arguments.database_type}")

    # Step 2: Build metadata
    dataset["metadata"] = {"database_type": arguments.metadata_database_type}
    if arguments.metadata_database_type == PrivateDatabaseType.PATH:
        # Store metadata from yaml to metadata collection
        with open(arguments.metadata_path, encoding="utf-8") as f:
            metadata_dict = yaml.safe_load(f)

        dataset["metadata"]["metadata_path"] = arguments.metadata_path

    elif arguments.metadata_database_type == PrivateDatabaseType.S3:
        client = boto3.client(
            "s3",
            endpoint_url=arguments.metadata_endpoint_url,
            aws_access_key_id=arguments.metadata_aws_access_key_id,
            aws_secret_access_key=arguments.metadata_aws_secret_access_key,
        )
        response = client.get_object(
            Bucket=arguments.metadata_s3_bucket, Key=arguments.metadata_s3_key
        )
        try:
            metadata_dict = yaml.safe_load(response["Body"])
        except yaml.YAMLError as e:
            raise e

        dataset["metadata"]["s3_bucket"] = arguments.metadata_s3_bucket
        dataset["metadata"]["s3_key"] = arguments.metadata_s3_key
        dataset["metadata"]["endpoint_url"] = arguments.metadata_endpoint_url
        dataset["metadata"][
            "aws_access_key_id"
        ] = arguments.metadata_aws_access_key_id
        dataset["metadata"][
            "aws_secret_access_key"
        ] = arguments.metadata_aws_secret_access_key

    else:
        raise ValueError(
            f"Unknown database type {arguments.metadata_database_type}"
        )

    # Step 3: Insert into db
    res = db.datasets.insert_one(dataset)
    check_result_acknowledged(res)
    res = db.metadata.insert_one({arguments.dataset: metadata_dict})
    check_result_acknowledged(res)

    LOG.info(
        f"Added dataset {arguments.dataset} with database "
        f"{arguments.database_type} and associated metadata."
    )


@connect
def add_datasets(db: Database, arguments: argparse.Namespace) -> None:
    """Set all database types to datasets in dataset collection based
    on yaml file.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_

    Raises:
        InternalServerException: _description_
        InternalServerException: _description_

    Returns:
        _type_: _description_
    """
    if arguments.clean:
        # Collection created from scratch
        db.datasets.drop()
        db.metadata.drop()
        LOG.info("Cleaning done. \n")

    with open(arguments.path, encoding="utf-8") as f:
        dataset_dict = yaml.safe_load(f)

    def verify_keys(d: dict, field: str, metadata: bool = False) -> None:
        """_summary_

        Args:
            d (dict): _description_
            field (str): _description_
            metadata (bool, optional): _description_. Defaults to False.
        """
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
            case PrivateDatabaseType.PATH:
                verify_keys(d, "dataset_path")
            case PrivateDatabaseType.S3:
                verify_keys(d, "s3_bucket")
                verify_keys(d, "s3_key")
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
    if existing_datasets:
        if arguments.overwrite_datasets:
            for d in existing_datasets:
                dataset_filter = {"dataset_name": d["dataset_name"]}
                update_operation = {"$set": d}
                res: _WriteResult = db.datasets.update_many(
                    dataset_filter, update_operation
                )
                check_result_acknowledged(res)
            LOG.info(
                f"Existing datasets updated with values"
                f"from yaml at {arguments.path}. "
            )
        else:
            warn(
                "Some datasets already present in database."
                "Overwrite is set to False."
            )

    # Add dataset collection
    if new_datasets:
        res = db.datasets.insert_many(new_datasets)
        check_result_acknowledged(res)
        LOG.info(f"Added datasets collection from yaml at {arguments.path}. ")

    # Step 2: add metadata collections (one metadata per dataset)
    for d in dataset_dict["datasets"]:
        dataset_name = d["dataset_name"]
        metadata_db_type = d["metadata"]["database_type"]

        verify_keys(d, "database_type", metadata=True)
        match metadata_db_type:
            case PrivateDatabaseType.PATH:
                verify_keys(d, "metadata_path", metadata=True)

                with open(
                    d["metadata"]["metadata_path"], encoding="utf-8"
                ) as f:
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
        metadata_filter = {dataset_name: metadata_dict}
        metadata = db.metadata.find_one(metadata_filter)

        if metadata and arguments.overwrite_metadata:
            LOG.info(f"Metadata updated for dataset : {dataset_name}.")
            res = db.metadata.update_one(
                metadata_filter, {"$set": {dataset_name: metadata_dict}}
            )
            check_result_acknowledged(res)
        elif metadata:
            LOG.info(
                "Metadata already exist. "
                "Use the command -om to overwrite with new values."
            )
        else:
            res = db.metadata.insert_one({dataset_name: metadata_dict})
            check_result_acknowledged(res)
            LOG.info(f"Added metadata of {dataset_name} dataset. ")


@connect
@check_dataset_and_metadata_exist(True)
def del_dataset(db: Database, arguments: argparse.Namespace) -> None:
    """Delete dataset from dataset collection.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    res = db.datasets.delete_many({"dataset_name": arguments.dataset})
    check_result_acknowledged(res)
    res = db.metadata.delete_many({arguments.dataset: {"$exists": True}})
    check_result_acknowledged(res)
    LOG.info(f"Deleted dataset and metadata for {arguments.dataset}.")


#######################  COLLECTIONS  ####################### # noqa: E266
@connect
def drop_collection(db: Database, arguments: argparse.Namespace) -> None:
    """Delete collection.

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    db.drop_collection(arguments.collection)
    LOG.info(f"Deleted collection {arguments.collection}.")


@connect
def show_collection(db: Database, arguments: argparse.Namespace) -> None:
    """Show a collection

    Args:
        db (Database): _description_
        arguments (argparse.Namespace): _description_
    """
    collection_query = db[arguments.collection].find({})
    collections = []
    for document in collection_query:
        document.pop("_id", None)
        collections.append(document)
    LOG.info(collections)


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

    #######################  DATASETS  ####################### # noqa: E266
    # Create parser for dataset private database
    add_dataset_parser = subparsers.add_parser(
        "add_dataset",
        help="set in which database the dataset is stored",
        parents=[connection_parser],
    )
    # Dataset location
    add_dataset_parser.add_argument("-d", "--dataset", required=True)
    add_dataset_parser.add_argument("-db", "--database_type", required=True)
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

    # Create the parser for the "del_dataset" command
    del_dataset_parser = subparsers.add_parser(
        "del_dataset",
        help="delete dataset and metadata from "
        "datasets and metadata collection",
        parents=[connection_parser],
    )
    del_dataset_parser.add_argument("-d", "--dataset", required=True, type=str)
    del_dataset_parser.set_defaults(func=del_dataset)

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
