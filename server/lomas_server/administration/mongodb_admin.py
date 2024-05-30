import argparse
import functools
from typing import Callable, Dict, List, Optional, Union
from warnings import warn

import boto3
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.results import _WriteResult
import yaml

from admin_database.utils import get_mongodb_url
from admin_database.mongodb_database import check_result_acknowledged
from constants import PrivateDatabaseType
from utils.collections_models import DatasetsCollection, UserCollection
from utils.error_handler import InternalServerException
from utils.loggr import LOG


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
        def wrapper_decorator(
            *arguments: argparse.Namespace, **kwargs: Dict
        ) -> None:
            db = arguments[0]
            user = arguments[1]

            user_count = db.users.count_documents({"user_name": user})

            if enforce_true and user_count == 0:
                raise ValueError(
                    f"User {user} does not exist in user collecion"
                )
            if not enforce_true and user_count > 0:
                raise ValueError(
                    f"User {user} already exists in user collection"
                )

            return function(*arguments, **kwargs)  # type: ignore

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
        def wrapper_decorator(
            *arguments: argparse.Namespace, **kwargs: Dict
        ) -> None:
            db = arguments[0]
            user = arguments[1]
            dataset = arguments[2]

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

            return function(*arguments, **kwargs)  # type: ignore

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
        def wrapper_decorator(
            *arguments: argparse.Namespace, **kwargs: Dict
        ) -> None:
            db = arguments[0]
            dataset = arguments[1]

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

            return function(*arguments, **kwargs)  # type: ignore

        return wrapper_decorator

    return inner_func


##########################  USERS  ########################## # noqa: E266
@check_user_exists(False)
def add_user(db: Database, user: str) -> None:
    """Add new user in users collection with initial values for all fields
    set by default.

    Args:
        db (Database): mongo database object
        user (str): username to be added

    Raises:
        ValueError: If the user already exists.
        WriteConcernError: If the result is not acknowledged.

    Returns:
        None
    """

    res = db.users.insert_one(
        {
            "user_name": user,
            "may_query": True,
            "datasets_list": [],
        }
    )

    check_result_acknowledged(res)

    LOG.info(f"Added user {user}.")


@check_user_exists(False)
def add_user_with_budget(
    db: Database, user: str, dataset: str, epsilon: float, delta: float
) -> None:
    """Add new user in users collection with initial values
    for all fields set by default.

    Args:
        db (Database): mongo database object
        user (str): username to be added
        dataset (str): name of the dataset to add to user
        epsilon (float): epsilon value for initial budget of user
        delta (float): delta value for initial budget of user

    Raises:
        ValueError: _description_

    Returns:
        None
    """
    res = db.users.insert_one(
        {
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
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Added access to user {user} with dataset {dataset}, "
        + f"budget epsilon {epsilon} and delta {delta}."
    )


@check_user_exists(True)
def del_user(db: Database, user: str) -> None:
    """Delete all related information for user from the users collection.

    Args:
        db (Database): mongo database object
        user (str): username to be deleted

    Returns:
        None
    """
    res = db.users.delete_many({"user_name": user})
    check_result_acknowledged(res)

    LOG.info(f"Deleted user {user}.")


@check_user_exists(True)
@check_user_has_dataset(False)
def add_dataset_to_user(
    db: Database, user: str, dataset: str, epsilon: float, delta: float
) -> None:
    """Add dataset with initialized budget values to list of datasets
    that the user has access to.
    Will not add if already added (no error will be raised in that case).

    Args:
        db (Database): mongo database object
        user (str): username of the user to check
        dataset (str): name of the dataset to add to user
        epsilon (float): epsilon value for initial budget of user
        delta (float): delta value for initial budget of user

    Raises:
        ValueError: _description_

    Returns:
        None
    """
    res = db.users.update_one(
        {
            "user_name": user,
            "datasets_list.dataset_name": {"$ne": dataset},
        },
        {
            "$push": {
                "datasets_list": {
                    "dataset_name": dataset,
                    "initial_epsilon": epsilon,
                    "initial_delta": delta,
                    "total_spent_epsilon": 0.0,
                    "total_spent_delta": 0.0,
                }
            }
        },
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Added access to dataset {dataset}"
        f"to user {user}"
        f" with budget epsilon {epsilon}"
        f" and delta {delta}."
    )


@check_user_exists(True)
@check_user_has_dataset(True)
def del_dataset_to_user(db: Database, user: str, dataset: str) -> None:
    """Remove if exists the dataset (and all related budget info)
    from list of datasets that user has access to.

    Args:
        db (Database): mongo database object
        user (str): username of the user to which to delete a dataset
        dataset (str): name of the dataset to remove from user

    Returns:
        None
    """
    res = db.users.update_one(
        {"user_name": user},
        {"$pull": {"datasets_list": {"dataset_name": {"$eq": dataset}}}},
    )

    check_result_acknowledged(res)

    LOG.info(f"Remove access to dataset {dataset}" + f" from user {user}.")


@check_user_exists(True)
@check_user_has_dataset(True)
def set_budget_field(
    db: Database, user: str, dataset: str, field: str, value: float
) -> None:
    """Set (for some reason) a budget field to a given value
    if given user exists and has access to given dataset.

    Args:
        db (Database): mongo database object
        user (str): username of the user to set budget to
        dataset (str): name of the dataset to set budget to
        field (str): one of 'epsilon' or 'delta'
        value (float): value to set as epsilon or delta

    Returns:
        None
    """
    res = db.users.update_one(
        {
            "user_name": user,
            "datasets_list.dataset_name": dataset,
        },
        {"$set": {f"datasets_list.$.{field}": value}},
    )

    check_result_acknowledged(res)

    LOG.info(
        f"Set budget of {user} for dataset {dataset}"
        f" of {field} to {value}."
    )


@check_user_exists(True)
def set_may_query(db: Database, user: str, value: bool) -> None:
    """Set (for some reason) the 'may query' field to a given value
    if given user exists.

    Args:
        db (Database): mongo database object
        user (str): username of the user to enable/disable
        value (bool): may query value (True or False)

    Returns:
        None
    """
    res = db.users.update_one(
        {"user_name": user},
        {"$set": {"may_query": (value == "True")}},
    )

    check_result_acknowledged(res)

    LOG.info(f"Set user {user} may query to True.")


@check_user_exists(True)
def show_user(db: Database, user: str) -> dict:
    """Show a user

    Args:
        db (Database): mongo database object
        user (str): username of the user to show

    Returns:
        user (dict): all information of user from 'users' collection
    """
    user_info = list(db.users.find({"user_name": user}))[0]
    user_info.pop("_id", None)
    LOG.info(user_info)
    return user_info


def add_users_via_yaml(
    db: Database,
    yaml_file: Union[str, Dict],
    clean: bool,
    overwrite: bool,
) -> None:
    """Add all users from yaml file to the user collection

    Args:
        db (Database): mongo database object
        yaml_file (Union[str, Dict]):
            if str: a path to the YAML file location
            if Dict: a dictionnary containing the collection data
        clean (bool): boolean flag
            True if drop current user collection
            False if keep current user collection
        overwrite (bool): boolean flag
            True if overwrite already existing users
            False errors if new values for already existing users

    Returns:
        None
    """
    if clean:
        # Collection created from scratch
        db.users.drop()
        LOG.info("Cleaning done. \n")

    # Load yaml data and insert it
    if isinstance(yaml_file, str):
        with open(yaml_file, encoding="utf-8") as f:
            yaml_file = yaml.safe_load(f)
    user_dict = UserCollection(**yaml_file)

    # Filter out duplicates
    new_users = []
    existing_users = []
    for user in user_dict.users:
        if not db.users.find_one({"user_name": user.user_name}):
            new_users.append(user)
        else:
            existing_users.append(user)

    # Overwrite values for existing user with values from yaml
    if existing_users:
        if overwrite:
            for user in existing_users:
                user_filter = {"user_name": user.user_name}
                update_operation = {"$set": user.dict()}
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
        new_users_dicts = [user.dict() for user in new_users]
        res = db.users.insert_many(new_users_dicts)
        check_result_acknowledged(res)
        LOG.info("Added user data from yaml.")
    else:
        LOG.info("No new users added, they already exist in the server")


def show_archives_of_user(db: Database, user: str) -> List[dict]:  # TODO  test
    """Show all previous queries from a user

    Args:
        db (Database): mongo database object
        user (str): username of the user to show archives

    Returns:
        archives (List): list of previous queries from the user
    """
    archives_infos: List[dict] = list(
        db.queries_archives.find({"user_name": user})
    )
    LOG.info(archives_infos)
    return archives_infos


def get_list_of_users(db: Database) -> list:  # TODO  test
    """Get the list of all users is 'users' collection

    Args:
        db (Database): mongo database object

    Returns:
        user_names (list): list of names of all users
    """
    user_names = []
    for elem in db.users.find():
        user_names.append(elem["user_name"])
    return user_names


def get_list_of_datasets_from_user(
    db: Database, user: str
) -> list:  # TODO  test
    """Get the list of all datasets from the user

    Args:
        db (Database): mongo database object
        user (str): username of the user to show archives

    Returns:
        user_datasets (list): list of names of all users
    """
    user_data = db.users.find_one({"user_name": user})
    if user_data:
        return [
            dataset["dataset_name"] for dataset in user_data["datasets_list"]
        ]
    else:
        return []


###################  DATASET TO DATABASE  ################### # noqa: E266
@check_dataset_and_metadata_exist(False)
def add_dataset(
    db: Database,
    dataset_name: str,
    database_type: str,
    metadata_database_type: str,
    dataset_path: Optional[str] = "",
    metadata_path: Optional[str] = "",
    s3_bucket: Optional[str] = "",
    s3_key: Optional[str] = "",
    endpoint_url: Optional[str] = "",
    aws_access_key_id: Optional[str] = "",
    aws_secret_access_key: Optional[str] = "",
    metadata_s3_bucket: Optional[str] = "",
    metadata_s3_key: Optional[str] = "",
    metadata_endpoint_url: Optional[str] = "",
    metadata_aws_access_key_id: Optional[str] = "",
    metadata_aws_secret_access_key: Optional[str] = "",
) -> None:
    """Set a database type to a dataset in dataset collection.

    Args:
        db (Database): mongo database object
        dataset_name (str): Dataset name
        database_type (str): Type of the database
        metadata_database_type (str): Metadata database type

        dataset_path (str): Path to the dataset (for local db type)
        metadata_path (str): Path to metadata (for local db type)

        s3_bucket (str): S3 bucket name
        s3_key (str): S3 key
        endpoint_url (str): S3 endpoint URL
        aws_access_key_id (str): AWS access key ID
        aws_secret_access_key (str): AWS secret access key
        metadata_s3_bucket (str): Metadata S3 bucket name
        metadata_s3_key (str): Metadata S3 key
        metadata_endpoint_url (str): Metadata S3 endpoint URL
        metadata_aws_access_key_id (str): Metadata AWS access key ID
        metadata_aws_secret_access_key (str): Metadata AWS secret access key

    Raises:
        ValueError: If the dataset already exists
                    or if the database type is unknown.

    Returns:
        None
    """
    if db.datasets.count_documents({"dataset_name": dataset_name}) > 0:
        raise ValueError("Cannot add database because already set. ")

    # Step 1: Build dataset
    dataset: Dict = {
        "dataset_name": dataset_name,
        "database_type": database_type,
    }

    if database_type == PrivateDatabaseType.PATH:
        dataset["dataset_path"] = dataset_path
    elif database_type == PrivateDatabaseType.S3:
        dataset["s3_bucket"] = s3_bucket
        dataset["s3_key"] = s3_key
        dataset["endpoint_url"] = endpoint_url
        dataset["aws_access_key_id"] = aws_access_key_id
        dataset["aws_secret_access_key"] = aws_secret_access_key
    else:
        raise ValueError(f"Unknown database type {database_type}")

    # Step 2: Build metadata
    dataset["metadata"] = {"database_type": metadata_database_type}
    if metadata_database_type == PrivateDatabaseType.PATH:
        # Store metadata from yaml to metadata collection
        with open(metadata_path, encoding="utf-8") as f:  # type: ignore
            metadata_dict = yaml.safe_load(f)

        dataset["metadata"]["metadata_path"] = metadata_path

    elif metadata_database_type == PrivateDatabaseType.S3:
        client = boto3.client(
            "s3",
            endpoint_url=metadata_endpoint_url,
            aws_access_key_id=metadata_aws_access_key_id,
            aws_secret_access_key=metadata_aws_secret_access_key,
        )
        response = client.get_object(
            Bucket=metadata_s3_bucket, Key=metadata_s3_key
        )
        try:
            metadata_dict = yaml.safe_load(response["Body"])
        except yaml.YAMLError as e:
            raise e

        dataset["metadata"]["s3_bucket"] = metadata_s3_bucket
        dataset["metadata"]["s3_key"] = metadata_s3_key
        dataset["metadata"]["endpoint_url"] = metadata_endpoint_url
        dataset["metadata"]["aws_access_key_id"] = metadata_aws_access_key_id
        dataset["metadata"][
            "aws_secret_access_key"
        ] = metadata_aws_secret_access_key

    else:
        raise ValueError(f"Unknown database type {metadata_database_type}")

    # Step 3: Insert into db
    res = db.datasets.insert_one(dataset)
    check_result_acknowledged(res)
    res = db.metadata.insert_one({dataset_name: metadata_dict})
    check_result_acknowledged(res)

    LOG.info(
        f"Added dataset {dataset_name} with database "
        f"{database_type} and associated metadata."
    )


def add_datasets_via_yaml(
    db: Database,
    yaml_file: Union[str, Dict],
    clean: bool,
    overwrite_datasets: bool,
    overwrite_metadata: bool,
) -> None:
    """Set all database types to datasets in dataset collection based
    on yaml file.

    Args:
        db (Database): mongo database object
        yaml_file (Union[str, Dict]):
            if str: a path to the YAML file location
            if Dict: a dictionnary containing the collection data
        clean (bool): Whether to clean the collection before adding.
        overwrite_datasets (bool): Whether to overwrite existing datasets.
        overwrite_metadata (bool): Whether to overwrite existing metadata.

    Raises:
        ValueError: If there are errors in the YAML file format.

    Returns:
        None
    """
    if clean:
        # Collection created from scratch
        db.datasets.drop()
        db.metadata.drop()
        LOG.info("Cleaning done. \n")

    if isinstance(yaml_file, str):
        with open(yaml_file, encoding="utf-8") as f:
            yaml_file = yaml.safe_load(f)
    dataset_dict = DatasetsCollection(**yaml_file)

    # Step 1: add datasets
    new_datasets = []
    existing_datasets = []
    for d in dataset_dict.datasets:
        # Fill datasets_list
        if not db.datasets.find_one({"dataset_name": d.dataset_name}):
            new_datasets.append(d)
        else:
            existing_datasets.append(d)

    # Overwrite values for existing dataset with values from yaml
    if existing_datasets:
        if overwrite_datasets:
            for d in existing_datasets:
                dataset_filter = {"dataset_name": d.dataset_name}
                update_operation = {"$set": d.dict()}
                res: _WriteResult = db.datasets.update_many(
                    dataset_filter, update_operation
                )
                check_result_acknowledged(res)
            LOG.info("Existing datasets updated with new collection")
        else:
            warn(
                "Some datasets already present in database."
                "Overwrite is set to False."
            )

    # Add dataset collection
    if new_datasets:
        new_datasets_dicts = [d.dict() for d in new_datasets]
        res = db.datasets.insert_many(new_datasets_dicts)
        check_result_acknowledged(res)
        LOG.info("Added datasets collection from yaml.")

    # Step 2: add metadata collections (one metadata per dataset)
    for d in dataset_dict.datasets:
        dataset_name = d.dataset_name
        metadata_db_type = d.metadata.database_type

        match metadata_db_type:
            case PrivateDatabaseType.PATH:
                with open(d.metadata.metadata_path, encoding="utf-8") as f:
                    metadata_dict = yaml.safe_load(f)

            case PrivateDatabaseType.S3:
                client = boto3.client(
                    "s3",
                    endpoint_url=d.metadata.endpoint_url,
                    aws_access_key_id=d.metadata.aws_access_key_id,
                    aws_secret_access_key=d.metadata.aws_secret_access_key,
                )
                response = client.get_object(
                    Bucket=d.metadata.s3_bucket,
                    Key=d.metadata.s3_key,
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

        if metadata and overwrite_metadata:
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


@check_dataset_and_metadata_exist(True)
def del_dataset(db: Database, dataset: str) -> None:
    """Delete dataset from dataset collection.

    Args:
        db (Database): mongo database object
        dataset (str): Dataset name to be deleted

    Returns:
        None
    """
    res = db.datasets.delete_many({"dataset_name": dataset})
    check_result_acknowledged(res)
    res = db.metadata.delete_many({dataset: {"$exists": True}})
    check_result_acknowledged(res)
    LOG.info(f"Deleted dataset and metadata for {dataset}.")


def show_dataset(db: Database, dataset: str) -> dict:  # TODO test
    """Show a dataset from dataset collection.

    Args:
        db (Database): mongo database object
        dataset (str): name of the dataset to show

    Returns:
        dataset_info (dict): informations about the dataset
    """
    dataset_info = list(db.datasets.find({"dataset_name": dataset}))[0]
    dataset_info.pop("_id", None)
    LOG.info(dataset_info)
    return dataset_info


def show_metadata_of_dataset(db: Database, dataset: str) -> dict:  # TODO test
    """Show a metadata from metadata collection.

    Args:
        db (Database): mongo database object
        dataset (str): name of the dataset of the metadata to show

    Returns:
        metadata (dict): informations about the metadata
    """
    # Retrieve the document containing metadata for the specified dataset
    metadata_document = db.metadata.find_one({dataset: {"$exists": True}})

    if metadata_document:
        # Extract metadata for the specified dataset
        metadata_info = metadata_document[dataset]
        return metadata_info
    else:
        raise ValueError(f"No metadata found for dataset: {dataset}")


def get_list_of_datasets(db: Database) -> list:  # TODO  test
    """Get the list of all dataset is 'datasets' collection

    Args:
        db (Database): mongo database object

    Returns:
        dataset_names (list): list of names of all datasets
    """
    dataset_names = []
    for elem in db.datasets.find():
        dataset_names.append(elem["dataset_name"])
    return dataset_names


#######################  COLLECTIONS  ####################### # noqa: E266
def drop_collection(db: Database, collection: str) -> None:
    """Delete collection.

    Args:
        db (Database): mongo database object
        collection (str): Collection name to be deleted.

    Returns:
        None
    """
    db.drop_collection(collection)
    LOG.info(f"Deleted collection {collection}.")


def show_collection(db: Database, collection: str) -> list:
    """Show a collection

    Args:
        db (Database): mongo database object
        collection (str): Collection name to be shown.

    Returns:
        None
    """
    collection_query = db[collection].find({})
    if not collection_query:
        return []

    collections = []
    for document in collection_query:
        document.pop("_id", None)
        collections.append(document)
    LOG.info(collections)
    return collections


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
        "add_users_via_yaml",
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
    users_collection_from_yaml_parser.set_defaults(func=add_users_via_yaml)

    # Function: Show Archives of User
    show_archives_parser = subparsers.add_parser(
        "show_archives",
        help="show all previous queries from a user",
        parents=[connection_parser],
    )
    show_archives_parser.add_argument(
        "-u",
        "--user",
        required=True,
        type=str,
        help="username of the user to show archives",
    )
    show_archives_parser.set_defaults(func=show_archives_of_user)

    # Function: Get List of Users
    get_users_parser = subparsers.add_parser(
        "get_users",
        help="get the list of all users in 'users' collection",
        parents=[connection_parser],
    )
    get_users_parser.set_defaults(func=get_list_of_users)

    # Function: Get List of Datasets from User
    get_user_datasets_parser = subparsers.add_parser(
        "get_user_datasets",
        help="get the list of all datasets from a user",
        parents=[connection_parser],
    )
    get_user_datasets_parser.add_argument(
        "-u",
        "--user",
        required=True,
        type=str,
        help="username of the user to show datasets",
    )
    get_user_datasets_parser.set_defaults(func=get_list_of_datasets_from_user)

    #######################  DATASETS  ####################### # noqa: E266
    # Create parser for dataset private database
    add_dataset_parser = subparsers.add_parser(
        "add_dataset",
        help="set in which database the dataset is stored",
        parents=[connection_parser],
    )
    # Dataset location
    add_dataset_parser.add_argument("-d", "--dataset_name", required=True)
    add_dataset_parser.add_argument("-db", "--database_type", required=True)
    add_dataset_parser.add_argument(
        "-d_path", "--dataset_path", required=False
    )
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

    # Create the parser for the "add_datasets_via_yaml" command
    add_datasets_via_yaml_parser = subparsers.add_parser(
        "add_datasets_via_yaml",
        help="create dataset to database type collection",
        parents=[connection_parser],
    )
    add_datasets_via_yaml_parser.add_argument(
        "-p", "--path", required=True, type=str
    )
    add_datasets_via_yaml_parser.add_argument(
        "-c",
        "--clean",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_via_yaml_parser.add_argument(
        "-od",
        "--overwrite_datasets",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_via_yaml_parser.add_argument(
        "-om",
        "--overwrite_metadata",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_via_yaml_parser.set_defaults(func=add_datasets_via_yaml)

    # Create the parser for the "del_dataset" command
    del_dataset_parser = subparsers.add_parser(
        "del_dataset",
        help="delete dataset and metadata from "
        "datasets and metadata collection",
        parents=[connection_parser],
    )
    del_dataset_parser.add_argument("-d", "--dataset", required=True, type=str)
    del_dataset_parser.set_defaults(func=del_dataset)

    # Function: Show Dataset
    show_dataset_parser = subparsers.add_parser(
        "show_dataset",
        help="show a dataset from the dataset collection",
        parents=[connection_parser],
    )
    show_dataset_parser.add_argument(
        "-d",
        "--dataset",
        required=True,
        type=str,
        help="name of the dataset to show",
    )
    show_dataset_parser.set_defaults(func=show_dataset)

    # Function: Show Metadata of Dataset
    show_metadata_parser = subparsers.add_parser(
        "show_metadata",
        help="show metadata from the metadata collection",
        parents=[connection_parser],
    )
    show_metadata_parser.add_argument(
        "-d",
        "--dataset",
        required=True,
        type=str,
        help="name of the dataset of the metadata to show",
    )
    show_metadata_parser.set_defaults(func=show_metadata_of_dataset)

    # Function: Get List of Datasets
    get_datasets_parser = subparsers.add_parser(
        "get_datasets",
        help="get the list of all datasets in 'datasets' collection",
        parents=[connection_parser],
    )
    get_datasets_parser.set_defaults(func=get_list_of_datasets)

    #######################  COLLECTIONS  ####################### # noqa: E266
    # Create the parser for the "drop_collection" command
    drop_collection_parser = subparsers.add_parser(
        "drop_collection",
        help="delete collection from database",
        parents=[connection_parser],
    )
    drop_collection_parser.add_argument(
        "-c",
        "--collection",
        required=True,
        choices=["users", "datasets", "metadata", "queries_archives"],
    )
    drop_collection_parser.set_defaults(func=drop_collection)

    # Create the parser for the "show_users_collection" command
    show_collection_parser = subparsers.add_parser(
        "show_collection",
        help="print a collection",
        parents=[connection_parser],
    )
    show_collection_parser.add_argument(
        "-c",
        "--collection",
        required=True,
        choices=["users", "datasets", "metadata", "queries_archives"],
    )
    show_collection_parser.set_defaults(func=show_collection)

    args = parser.parse_args()

    #######################  FUNCTION CALL  ###################### # noqa: E266
    # Get MongoDB
    db_url = get_mongodb_url(args)
    mongo_db: Database = MongoClient(db_url)[args.db_name]

    function_map = {
        "add_user": lambda args: add_user(mongo_db, args.user),
        "add_user_with_budget": lambda args: add_user_with_budget(
            mongo_db, args.user, args.dataset, args.epsilon, args.delta
        ),
        "del_user": lambda args: del_user(mongo_db, args.user),
        "add_dataset_to_user": lambda args: add_dataset_to_user(
            mongo_db, args.user, args.dataset, args.epsilon, args.delta
        ),
        "del_dataset_to_user": lambda args: del_dataset_to_user(
            mongo_db, args.user, args.dataset
        ),
        "set_budget_field": lambda args: set_budget_field(
            mongo_db, args.user, args.dataset, args.field, args.value
        ),
        "set_may_query": lambda args: set_may_query(
            mongo_db, args.user, args.value
        ),
        "show_user": lambda args: show_user(mongo_db, args.user),
        "add_users_via_yaml": lambda args: add_users_via_yaml(
            mongo_db, args.path, args.clean, args.overwrite
        ),
        "show_archives": lambda args: show_archives_of_user(
            mongo_db, args.user
        ),
        "get_users": lambda args: get_list_of_users(mongo_db),
        "get_user_datasets": lambda args: get_list_of_datasets_from_user(
            mongo_db, args.user
        ),
        "add_dataset": lambda args: add_dataset(
            mongo_db,
            args.dataset_name,
            args.database_type,
            args.metadata_database_type,
            args.dataset_path,
            args.metadata_path,
            args.s3_bucket,
            args.s3_key,
            args.endpoint_url,
            args.aws_access_key_id,
            args.aws_secret_access_key,
            args.metadata_s3_bucket,
            args.metadata_s3_key,
            args.metadata_endpoint_url,
            args.metadata_aws_access_key_id,
            args.metadata_aws_secret_access_key,
        ),
        "add_datasets_via_yaml": lambda args: add_datasets_via_yaml(
            mongo_db,
            args.path,
            args.clean,
            args.overwrite_datasets,
            args.overwrite_metadata,
        ),
        "del_dataset": lambda args: del_dataset(mongo_db, args.dataset),
        "show_dataset": lambda args: show_dataset(mongo_db, args.dataset),
        "show_metadata": lambda args: show_metadata_of_dataset(
            mongo_db, args.dataset
        ),
        "get_datasets": lambda args: get_list_of_datasets(mongo_db),
        "drop_collection": lambda args: drop_collection(
            mongo_db, args.collection
        ),
        "show_collection": lambda args: show_collection(
            mongo_db, args.collection
        ),
    }
    function_map[args.func](args)
