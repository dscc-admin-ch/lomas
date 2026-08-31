import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from uuid import UUID

from csvw_eo.metadata_structure import TableMetadata
from fastapi import UploadFile

from lomas_core.models.collections import DSInfo, User
from lomas_core.models.constants import get_lomas_logger
from lomas_core.models.responses import Budget, Job
from lomas_server.admin_database.constants import BudgetDBKey, TopDBKey

logger = get_lomas_logger(__name__)


class AdminDatabase(ABC):
    """Overall database management for server state."""

    # Jobs
    ###########################################################################

    @abstractmethod
    def does_job_exist(self, uid: UUID) -> bool:
        """Returns true only if the job exists.

        Args:
            uid (UUID): The uid of the job.

        Returns:
            bool: True only if the job exists
        """

    @abstractmethod
    def get_job(self, uid: UUID) -> Job:
        """
        Gets the job with given uid from the database.

        Args:
            uid (UUID): The uid of the job.

        Returns:
            Job: The job.
        """

    @abstractmethod
    def get_job_pending(self) -> Job:
        """Gets the next pending job from the database.

        Returns:
            Job: The next pending job.
        """

    @abstractmethod
    def put_job(self, job: Job) -> None:
        """
        Puts the job in the database.

        Args:
            job (Job): The job to put in the database.
        """

    @abstractmethod
    def update_job(self, updated_job: Job) -> None:
        """
        Updates the job.

        All fields are taken from updated_job, except those that are None.

        Args:
            updated_job (Job): The updated job
        """

    # Archives
    ###########################################################################

    @abstractmethod
    def archive_job(self, uid: UUID) -> None:
        """
        Adds the job into the archives, ignores dummy and cost queries.

        Args:
            uid (UUID): The job uid to archive
        """

    @abstractmethod
    def get_user_dataset_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> list[dict]:
        """
        Retrieves and return the queries already done by a user for a particular dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[dict]: List of previous queries.
        """

    @abstractmethod
    def get_user_queries(self, username: str) -> list[Job]:
        """
        Retrieves and return the queries already done by a user.

        Args:
            user_name (str): name of the user

        Returns:
            List[dict]: List of previous queries.
        """

    # Users
    ###########################################################################

    @abstractmethod
    def users(self) -> list[User]:
        """Get the list of all users."""

    @abstractmethod
    def get_user(self, user_name: str, current_conn: sqlite3.Connection | None = None) -> User:
        """Get a user given its name.

        Args:
            user_name (str): The name of the user to get.
            current_conn (sqlite3.Connection | None, optional): The sqlite3 connection context. Enables multiple calls can be made within the a single transaction. Defaults to None.

        Returns:
            User: The user.
        """

    @abstractmethod
    def replace_user(self, user: User, current_conn: sqlite3.Connection | None = None) -> None:
        """Replaces the existing user in the database with the one provided.

        Args:
            user (User) (str): The user to replace
            current_conn (sqlite3.Connection | None, optional): The sqlite3 connection context. Enables multiple calls can be made within the a single transaction. Defaults to None.
        """

    @abstractmethod
    def add_dataset_to_user(self, username: str, dataset_name: str, initial_budget: Budget) -> None:
        """Add a new dataset to an existing user.

        Args:
            username (str): The name of the user to add a dataset to.
            dataset_name (str): The name of the dataset to add.
            initial_budget (Budget): The initial budget for that user and dataset.
        """

    @abstractmethod
    def del_dataset_to_user(self, username: str, dataset_name: str) -> None:
        """Delete a dataset from a user.

        Args:
            username (str): The name of the user.
            dataset_name (str): The dataset to remove.
        """

    @abstractmethod
    def add_users_via_yaml(
        self, yaml_file: Path | BinaryIO | SpooledTemporaryFile, clean: bool, overwrite: bool
    ) -> None:
        """Add a collection of users via a yaml file.

        Args:
            yaml_file (Path | BinaryIO | SpooledTemporaryFile): The file containting the user collection.
            clean (bool): Whether to remove all existing users beforehand.
            overwrite (bool): Whether to overwrite existing users.
        """

    @abstractmethod
    def put_user(self, user: User) -> None:
        """Add new user in users collection with default values for all fields.

        Args:
            user (User): user to be added

        Raises:
            ValueError: If the username already exists.

        Returns:
            None
        """

    @abstractmethod
    def del_user(self, user_name: str) -> None:
        """Deletes the user from the database.

        Args:
            user_name (str): The user name.
        """

    @abstractmethod
    def does_user_exist(self, user_name: str) -> bool:
        """
        Checks if user exist in the database.

        Args:
            user_name (str): name of the user to check

        Returns:
            bool: True if the user exists, False otherwise.
        """

    @abstractmethod
    def is_user_admin(self, user_name: str) -> bool:
        """
        Returns true if the user is an admin.

        Args:
            user_name (str): name of the user

        Returns:
            bool: True if the user is a lomas admin.
        """

    @abstractmethod
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        """
        Checks if a user may access a particular dataset.

        Wrapped by [user_must_exist][lomas_server.admin_database.admin_database.user_must_exist].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            bool: True if the user has access, False otherwise.
        """

    @abstractmethod
    def get_budget(self, user_name: str, dataset_name: str, parameter: BudgetDBKey) -> Budget:
        """
        Get the specified budget by user on dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): Member of BudgetDBKey.

        Returns:
            Budget: The requested budget value.
        """

    @abstractmethod
    def set_budget(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        value: Budget,
    ) -> None:
        """Sets new budget value for user, dataset and given parameter.

        Args:
            user_name (str): The user name.
            dataset_name (str): The dataset name.
            parameter (BudgetDBKey): Member of BudgetDBKey
            value (Budget): The new budget value to set.
        """

    def get_total_spent_budget(self, user_name: str, dataset_name: str) -> Budget:
        """
        Get the total spent epsilon and delta spent by user on dataset.

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            Budget: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return self.get_budget(user_name, dataset_name, BudgetDBKey.SPENT)

    def get_initial_budget(self, user_name: str, dataset_name: str) -> Budget:
        """
        Get the initial epsilon and delta budget.

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            Budget: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return self.get_budget(user_name, dataset_name, BudgetDBKey.INITIAL)

    def get_remaining_budget(self, user_name: str, dataset_name: str) -> Budget:
        """
        Get the remaining epsilon and delta budget (initial - total spent).

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            Budget: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return self.get_initial_budget(user_name, dataset_name) - self.get_total_spent_budget(
            user_name, dataset_name
        )

    # Datasets
    ###########################################################################

    @abstractmethod
    def datasets(self) -> list[DSInfo]:
        """Returns the list of all datasets."""

    @abstractmethod
    def add_datasets_via_yaml(
        self,
        yaml_file: Path | BinaryIO | SpooledTemporaryFile,
        clean: bool,
        path_prefix: Path = Path(),
    ) -> None:
        """Add a collection of datasets from a yaml file.

        Args:
            yaml_file (Path | BinaryIO | SpooledTemporaryFile): The yaml file containing the dataset infos.
            clean (bool): Whether to remove all datasets beforehand.
            path_prefix (Path, optional): The path prefix to preprend to all paths specified in the dataset infos.. Defaults to Path().
        """

    @abstractmethod
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

    @abstractmethod
    def del_dataset(self, dataset_name: str) -> None:
        """Delete a dataset.

        Args:
            dataset_name (str): The dataset name.
        """

    @abstractmethod
    def does_dataset_exist(self, dataset_name: str) -> bool:
        """
        Checks if dataset exists in the database.

        Args:
            dataset_name (str): name of the dataset to check

        Returns:
            bool: True if the dataset exists, False otherwise.
        """

    @abstractmethod
    def get_dataset(self, dataset_name: str) -> DSInfo:
        """
        Get dataset access info based on dataset_name.

        Args:
            dataset_name (str): Name of the dataset.

        Returns:
            Dataset: The dataset model.
        """

    @abstractmethod
    def get_dataset_metadata(self, dataset_name: str) -> TableMetadata:
        """
        Returns the metadata dictionnary of the dataset.

        Wrapped by [dataset_must_exist][lomas_server.admin_database.admin_database.dataset_must_exist].

        Args:
            dataset_name (str): name of the dataset to get the metadata

        Returns:
            TableMetadata: The metadata object.
        """

    @abstractmethod
    def set_dataset_metadata(self, dataset_name: str, json_file: UploadFile) -> None:
        """Set new metadata for a given dataset.

        Args:
            dataset_name (str): The dataset name.
            json_file (UploadFile): The metadata file.
        """

    # Other
    ###########################################################################

    @abstractmethod
    def drop_collection(self, collection: TopDBKey) -> None:
        """Remove entire collection from the database.

        Args:
            collection (TopDBKey): One of TopDBKey
        """

    @abstractmethod
    def wipe(self) -> None:
        """Wipe the entire Database."""

    @abstractmethod
    def set_bootstrap(self, bootstrap: str) -> None:
        """Sets the bootstrap value.

        Also sets the bootstrap disabled value to False.

        Args:
            bootstrap (str): Bootstrap creds to set.
        """

    @abstractmethod
    def get_bootstrap(self) -> str | None:
        """Returns the bootstrap credential value or None if it has not been set.

        Returns:
            str | None: The bootstrap credential value or None if it has not been set.
        """

    @abstractmethod
    def set_bootstrap_disabled(self, bootstrap_disabled: bool = True) -> None:
        """Sets the bootstrap disabled value."""

    @abstractmethod
    def get_bootstrap_disabled(self) -> bool:
        """Get the bootstrap disabled value.

        Returns:
            bool: The bootstrap disabled value. False by default if not set in the DB.
        """
