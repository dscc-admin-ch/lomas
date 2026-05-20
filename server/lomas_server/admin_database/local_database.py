import json
import operator as op
import shelve
import sys
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO, Self

import boto3
import yaml
from csvw_eo.metadata_structure import TableMetadata
from fastapi import UploadFile
from pydantic import HttpUrl

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import (
    DatasetOfUser,
    DatasetsCollection,
    DSInfo,
    DSPathAccess,
    DSS3Access,
    User,
    UserCollection,
    UserId,
)
from lomas_core.models.constants import PrivateDatabaseType, get_lomas_logger
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import QueryResponse
from lomas_server.admin_database.admin_database import (
    AdminDatabase,
    dataset_must_exist,
    user_must_exist,
    user_must_have_access_to_dataset,
)
from lomas_server.admin_database.constants import BudgetDBKey, TopDBKey as TK

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


logger = get_lomas_logger(__name__)


class LocalAdminDatabase(AdminDatabase):
    """Local Admin database in a single file."""

    path: Path
    """Database accepts existing path or new (creatable) path."""

    def model_post_init(self, _: Any, /) -> None:
        # create the file if it doesn't exists yet (makes open with flag='r' safe)
        shelve.open(self.path).close()

    @override
    def wipe(self) -> None:
        if (p := Path(self.path)).exists():
            p.unlink()

    def load_users_collection(self, users: list[User]) -> None:
        with shelve.open(self.path, writeback=True) as db:
            db[TK.USERS] = {user.id.name: user.model_dump() for user in users}

    def users(self) -> list[User]:
        with shelve.open(self.path, flag="r") as db:
            return list(map(User.model_validate, db.get(TK.USERS, {}).values()))

    def load_dataset_collection(self, datasets: list[DSInfo], path_prefix: Path) -> None:
        with shelve.open(self.path, writeback=True) as db:
            # Step 1: add datasets
            new_datasets = []
            for ds in datasets:
                # Overwrite path
                if isinstance(ds.dataset_access, DSPathAccess):
                    match ds.dataset_access.path:
                        case HttpUrl():
                            pass
                        case Path():
                            ds.dataset_access.path = path_prefix / ds.dataset_access.path
                if isinstance(ds.metadata_access, DSPathAccess):
                    match ds.metadata_access.path:
                        case HttpUrl():
                            pass
                        case Path():
                            ds.metadata_access.path = path_prefix / ds.metadata_access.path

                # Fill datasets_list
                new_datasets.append(ds)

            # Add dataset collection
            if new_datasets:
                new_datasets_dicts = [ds.model_dump() for ds in new_datasets]
                db[TK.DATASETS] = new_datasets_dicts

            db[TK.METADATA] = {}
            # Step 2: add metadata collections (one metadata per dataset)
            for ds in datasets:
                dataset_name = ds.dataset_name
                metadata_access = ds.metadata_access

                match metadata_access:
                    case DSPathAccess():
                        with metadata_access.path.open("r", encoding="utf-8") as f:
                            metadata_dict = json.load(f)

                    case DSS3Access():
                        client = boto3.client(
                            "s3",
                            endpoint_url=str(metadata_access.endpoint_url),
                            aws_access_key_id=metadata_access.access_key_id,
                            aws_secret_access_key=metadata_access.secret_access_key,
                        )
                        response = client.get_object(
                            Bucket=metadata_access.bucket,
                            Key=metadata_access.key,
                        )
                        try:
                            metadata_dict = json.loads(response["Body"].read())
                        except json.JSONDecodeError as e:
                            raise e

                    case _:
                        raise InternalServerException(
                            f"Unknown metadata_db_type PrivateDatabaseType: {metadata_access.database_type}"
                        )
                db[TK.METADATA][dataset_name] = TableMetadata.from_dict(metadata_dict).model_dump()
                logger.info(f"Added metadata of {dataset_name} dataset.")

    def datasets(self) -> list[DSInfo]:
        with shelve.open(self.path, flag="r") as db:
            return list(map(DSInfo.model_validate, db.get(TK.DATASETS, [])))

    def add_datasets_via_yaml(
        self,
        yaml_file: Path | BinaryIO | SpooledTemporaryFile,
        clean: bool,
        path_prefix: Path = Path(),
    ) -> None:
        """Set all database types to datasets in dataset collection based.

        on yaml file.

        Args:
            yaml_file Path: path to the YAML file location
            clean (bool): Whether to clean the collection before adding.
            path_prefix (Path, optional): Prefix to add to all file paths. Defaults to empty Path.

        Raises:
            ValueError: If there are errors in the YAML file format.

        Returns:
            None
        """
        if clean:
            self.drop_collection("datasets")

        match yaml_file:
            case Path():
                yaml_dict = yaml.safe_load(yaml_file.resolve().open(encoding="utf-8"))
            case BinaryIO() | SpooledTemporaryFile():
                yaml_dict = yaml.safe_load(yaml_file)
        self.load_dataset_collection(DatasetsCollection(**yaml_dict).datasets, path_prefix)

    def add_dataset(
        self,
        dataset_name: str,
        database_type: str,
        metadata_database_type: str,
        dataset_path: str | None = "",
        metadata_path: str = "",
        bucket: str | None = "",
        key: str | None = "",
        endpoint_url: str | None = "",
        credentials_name: str | None = "",
        metadata_bucket: str | None = "",
        metadata_key: str | None = "",
        metadata_endpoint_url: str | None = "",
        metadata_access_key_id: str | None = "",
        metadata_secret_access_key: str | None = "",
        metadata_credentials_name: str | None = "",
    ) -> None:
        """Set a database type to a dataset in dataset collection.

        Args:
            dataset_name (str): Dataset name
            database_type (str): Type of the database
            metadata_database_type (str): Metadata database type

            dataset_path (str): Path to the dataset (for local db type)
            metadata_path (str): Path to metadata (for local db type)

            bucket (str): S3 bucket name
            key (str): S3 key
            endpoint_url (str): S3 endpoint URL
            credentials_name (str): The name of the credentials in the\
                server config to retrieve the dataset from S3 storage.
            metadata_bucket (str): Metadata S3 bucket name
            metadata_key (str): Metadata S3 key
            metadata_endpoint_url (str): Metadata S3 endpoint URL
            metadata_access_key_id (str): Metadata AWS access key ID
            metadata_secret_access_key (str): Metadata AWS secret access key
            metadata_credentials_name (str): The name of the credentials in the\
                server config for retrieving the metadata.

        Raises:
            ValueError: If the dataset already exists
                        or if the database type is unknown.

        Returns:
            None
        """
        # Step 1: Build dataset
        dataset: dict[str, Any] = {"dataset_name": dataset_name}

        dataset_access: dict[str, Any] = {
            "database_type": database_type,
        }

        if database_type == PrivateDatabaseType.PATH:
            if dataset_path is None:
                raise ValueError("Dataset path not set.")
            dataset_access["path"] = dataset_path
        elif database_type == PrivateDatabaseType.S3:
            dataset_access["bucket"] = bucket
            dataset_access["key"] = key
            dataset_access["endpoint_url"] = endpoint_url
            dataset_access["credentials_name"] = credentials_name
        else:
            raise ValueError(f"Unknown database type {database_type}")

        dataset["dataset_access"] = dataset_access

        # Step 2: Build metadata
        metadata_access: dict[str, Any] = {"database_type": metadata_database_type}
        if metadata_database_type == PrivateDatabaseType.PATH:
            # Store metadata to metadata collection
            metadata_dict = json.loads(Path(metadata_path).resolve().read_text(encoding="utf-8"))
            metadata_access["path"] = metadata_path

        elif metadata_database_type == PrivateDatabaseType.S3:
            client = boto3.client(
                "s3",
                endpoint_url=metadata_endpoint_url,
                aws_access_key_id=metadata_access_key_id,
                aws_secret_access_key=metadata_secret_access_key,
            )
            response = client.get_object(Bucket=metadata_bucket, Key=metadata_key)
            try:
                metadata_dict = json.loads(response["Body"].read().decode("utf-8"))
            except yaml.YAMLError as e:
                raise e

            metadata_access["bucket"] = metadata_bucket
            metadata_access["key"] = metadata_key
            metadata_access["endpoint_url"] = metadata_endpoint_url
            metadata_access["credentials_name"] = metadata_credentials_name

        else:
            raise ValueError(f"Unknown database type {metadata_database_type}")

        dataset["metadata_access"] = metadata_access

        # Step 3: Validate
        ds_info = DSInfo.model_validate(dataset)
        validated_dataset = ds_info.model_dump()
        validated_metadata = TableMetadata.from_dict(metadata_dict).model_dump()

        # Step 4: Insert into db
        with shelve.open(self.path, writeback=True) as db:
            db[TK.DATASETS] = [*db.get(TK.DATASETS, []), validated_dataset]
            db[TK.METADATA] = db.get(TK.METADATA, {}) | {dataset_name: validated_metadata}
            db.sync()

    def del_dataset(self, dataset_name: str) -> None:
        with shelve.open(self.path, writeback=True) as db:
            for ds in db[TK.DATASETS]:
                if ds["dataset_name"] == dataset_name:
                    db[TK.DATASETS].remove(ds)

    def add_dataset_to_user(self, username: str, dataset_name: str, epsilon: float, delta: float) -> None:
        with shelve.open(self.path, writeback=True) as db:
            user = User.model_validate(db[TK.USERS][username])
            ds = DatasetOfUser(dataset_name=dataset_name, initial_epsilon=epsilon, initial_delta=delta)
            user_updated = User(
                id=user.id,
                may_query=user.may_query,
                datasets_list=[*user.datasets_list, ds],
            )
            db[TK.USERS][username] = user_updated.model_dump()

    def del_dataset_to_user(self, username: str, dataset_name: str) -> None:
        with shelve.open(self.path, writeback=True) as db:
            user = User.model_validate(db[TK.USERS][username])
            user_updated = User(
                id=user.id,
                may_query=user.may_query,
                datasets_list=[dsu for dsu in user.datasets_list if dsu.dataset_name != dataset_name],
            )
            db[TK.USERS][username] = user_updated.model_dump()

    def add_users_via_yaml(self, yaml_file: Path | BinaryIO | SpooledTemporaryFile, clean: bool) -> None:
        """Add all users from yaml file to the user collection.

        Args:
            yaml_file (Path): a path to the YAML file location
            clean (bool): boolean flag
                True if drop current user collection
                False if keep current user collection

        Returns:
            None
        """
        if clean:
            self.drop_collection("users")

        # Load yaml data and insert it
        match yaml_file:
            case Path():
                yaml_dict = yaml.safe_load(yaml_file.resolve().open(encoding="utf-8"))
            case BinaryIO() | SpooledTemporaryFile():
                yaml_dict = yaml.safe_load(yaml_file)
        self.load_users_collection(UserCollection(**yaml_dict).users)

    def add_user(
        self,
        username: str,
        email: str,
        dataset_name: str | None = None,
        epsilon: float = 0.0,
        delta: float = 0.0,
    ) -> None:
        """Add new user in users collection with default values for all fields.

        Args:
            username (str): username to be added
            email (str): email to be added

        Raises:
            ValueError: If the username already exists.
            WriteConcernError: If the result is not acknowledged.

        Returns:
            None
        """
        validated_user = User(
            id=UserId(name=username, email=email),
            may_query=True,
            datasets_list=(
                []
                if dataset_name is None
                else [DatasetOfUser(dataset_name=dataset_name, initial_epsilon=epsilon, initial_delta=delta)]
            ),
        ).model_dump()

        with shelve.open(self.path, writeback=True) as db:
            if "users" not in db:
                db[TK.USERS] = {}
            db[TK.USERS][username] = validated_user

    @user_must_exist
    def del_user(self, username: str) -> None:
        with shelve.open(self.path, writeback=True) as db:
            del db[TK.USERS][username]

    @override
    def does_user_exist(self, user_name: str) -> bool:
        return user_name in map(lambda user: user.id.name, self.users())

    @override
    def does_dataset_exist(self, dataset_name: str) -> bool:
        return dataset_name in map(lambda ds: ds.dataset_name, self.datasets())

    @override
    @dataset_must_exist
    def get_dataset(self, dataset_name: str) -> DSInfo:
        with shelve.open(self.path, flag="r") as db:
            dataset = next(filter(lambda ds: ds["dataset_name"] == dataset_name, db[TK.DATASETS]))
            return DSInfo.model_validate(dataset)

    @override
    @dataset_must_exist
    def get_dataset_metadata(self, dataset_name: str) -> TableMetadata:
        with shelve.open(self.path, flag="r") as db:
            metadata = db.get(TK.METADATA, {}).get(dataset_name)
            return TableMetadata.model_validate(metadata)

    @dataset_must_exist
    def set_dataset_metadata(self, dataset_name: str, json_file: UploadFile) -> None:
        json_file.seek(0)
        content = json_file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        metadata_dict = json.loads(content)
        validated_metadata = TableMetadata.from_dict(metadata_dict).model_dump()
        with shelve.open(self.path, writeback=True) as db:
            db[TK.METADATA] = db.get(TK.METADATA, {}) | {dataset_name: validated_metadata}

    @override
    @user_must_exist
    def is_user_admin(self, user_name: str) -> bool:
        with shelve.open(self.path, flag="r") as db:
            return db[TK.USERS][user_name]["admin"]

    @override
    @user_must_exist
    def get_and_set_may_user_query(self, user_name: str, may_query: bool) -> bool:
        with shelve.open(self.path, writeback=True) as db:
            previous_may_query = db[TK.USERS][user_name]["may_query"]
            db[TK.USERS][user_name]["may_query"] = may_query
            return previous_may_query

    @override
    @user_must_exist
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        @dataset_must_exist
        def has_access_to_dataset(self: Self, dataset_name: str) -> bool:
            with shelve.open(self.path, flag="r") as db:
                return bool(
                    [
                        ds
                        for ds in db[TK.USERS][user_name]["datasets_list"]
                        if ds["dataset_name"] == dataset_name
                    ]
                )

        return has_access_to_dataset(self, dataset_name)

    @override
    def get_epsilon_or_delta(self, user_name: str, dataset_name: str, parameter: BudgetDBKey) -> float:
        with shelve.open(self.path, flag="r") as db:
            return sum(
                map(
                    op.itemgetter(parameter),
                    filter(
                        lambda ds: ds["dataset_name"] == dataset_name,
                        db[TK.USERS][user_name]["datasets_list"],
                    ),
                )
            )

    @override
    def update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        spent_value: float,
    ) -> None:
        with shelve.open(self.path, writeback=True) as db:
            datasets = db[TK.USERS][user_name]["datasets_list"]
            for ds in datasets:
                if ds["dataset_name"] == dataset_name:
                    ds[parameter] += spent_value

    def set_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        value: float,
    ) -> None:
        with shelve.open(self.path, writeback=True) as db:
            datasets = db[TK.USERS][user_name]["datasets_list"]
            for ds in datasets:
                if ds["dataset_name"] == dataset_name:
                    ds[parameter] = value

    @override
    @user_must_have_access_to_dataset
    def get_user_previous_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> list[dict]:
        def match(archive: dict[str, str]) -> bool:
            return (user_name, dataset_name) == op.itemgetter("user_name", "dataset_name")(archive)

        with shelve.open(self.path, flag="r") as db:
            return list(filter(match, db.get(TK.ARCHIVE, [])))

    @override
    def save_query(self, user_name: str, query: LomasRequestModel, response: QueryResponse) -> None:
        with shelve.open(self.path, writeback=True) as db:
            to_archive = self.prepare_save_query(user_name, query, response)
            if TK.ARCHIVE not in db:
                db[TK.ARCHIVE] = [to_archive]
            else:
                db[TK.ARCHIVE].append(to_archive)

    def get_archives_of_user(self, username: str) -> list[dict]:
        with shelve.open(self.path, flag="r") as db:
            return [archive for archive in db.get(TK.ARCHIVE, []) if archive["user_name"] == username]

    def drop_collection(self, collection: str) -> None:
        with shelve.open(self.path, writeback=True) as db:
            if collection in db:
                del db[collection]
