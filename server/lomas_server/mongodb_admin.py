import argparse
import functools
from typing import Callable, Dict, List, Optional, Union
from warnings import warn

import boto3
import yaml
from pymongo.database import Database
from pymongo.results import _WriteResult

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
                    f"User {user} does not exist in user collection"
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
                    f"Dataset {dataset} does not exist in dataset collection"
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
                    " not exist in metadata collection"
                )
            if not enforce_true and metadata_count > 0:
                raise ValueError(
                    f"Metadata for dataset {dataset} already"
                    " exists in metadata collection"
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
        f" to user {user}"
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

    LOG.info(f"Set user {user} may query to {value}.")


@check_user_exists(True)
def get_user(db: Database, user: str) -> dict:
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
                update_operation = {"$set": user.model_dump()}
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
        new_users_dicts = [user.model_dump() for user in new_users]
        res = db.users.insert_many(new_users_dicts)
        check_result_acknowledged(res)
        LOG.info("Added user data from yaml.")
    else:
        LOG.info("No new users added, they already exist in the server")


@check_user_exists(True)
def get_archives_of_user(db: Database, user: str) -> List[dict]:
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


def get_list_of_users(db: Database) -> list:
    """Get the list of all users is 'users' collection

    Args:
        db (Database): mongo database object

    Returns:
        user_names (list): list of names of all users
    """
    user_names = []
    for elem in db.users.find():
        user_names.append(elem["user_name"])
    LOG.info(user_names)
    return user_names


@check_user_exists(True)
def get_list_of_datasets_from_user(db: Database, user: str) -> list:
    """Get the list of all datasets from the user

    Args:
        db (Database): mongo database object
        user (str): username of the user to show archives

    Returns:
        user_datasets (list): list of names of all users
    """
    user_data = db.users.find_one({"user_name": user})
    assert user_data is not None, "User must exist"
    LOG.info(
        [dataset["dataset_name"] for dataset in user_data["datasets_list"]]
    )
    return [dataset["dataset_name"] for dataset in user_data["datasets_list"]]


###################  DATASET TO DATABASE  ################### # noqa: E266
@check_dataset_and_metadata_exist(False)
def add_dataset(  # pylint: disable=too-many-arguments, too-many-locals
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


def add_datasets_via_yaml(  # pylint: disable=R0912, R0914, R0915
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
                update_operation = {"$set": d.model_dump()}
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
        new_datasets_dicts = [d.model_dump() for d in new_datasets]
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


@check_dataset_and_metadata_exist(True)
def get_dataset(db: Database, dataset: str) -> dict:
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


@check_dataset_and_metadata_exist(True)
def get_metadata_of_dataset(db: Database, dataset: str) -> dict:
    """Show a metadata from metadata collection.

    Args:
        db (Database): mongo database object
        dataset (str): name of the dataset of the metadata to show

    Returns:
        metadata (dict): informations about the metadata
    """
    # Retrieve the document containing metadata for the specified dataset
    metadata_document = db.metadata.find_one({dataset: {"$exists": True}})
    assert metadata_document is not None, "Metadata must exist"

    # Extract metadata for the specified dataset
    metadata_info = metadata_document[dataset]
    LOG.info(metadata_info)
    return metadata_info


def get_list_of_datasets(db: Database) -> list:
    """Get the list of all dataset is 'datasets' collection

    Args:
        db (Database): mongo database object

    Returns:
        dataset_names (list): list of names of all datasets
    """
    dataset_names = []
    for elem in db.datasets.find():
        dataset_names.append(elem["dataset_name"])
    LOG.info(dataset_names)
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


def get_collection(db: Database, collection: str) -> list:
    """Show a collection

    Args:
        db (Database): mongo database object
        collection (str): Collection name to be shown.

    Returns:
        None
    """
    collection_query = db[collection].find({})
    collections = []
    for document in collection_query:
        document.pop("_id", None)
        collections.append(document)
    LOG.info(collections)
    return collections
