from datetime import datetime, timezone
from typing import List

import yaml
from lomas_core.error_handler import (
    InvalidQueryException,
)
from lomas_core.models.collections import DSInfo, Metadata
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import QueryResponse

from lomas_server.admin_database.admin_database import (
    AdminDatabase,
    dataset_must_exist,
    user_must_exist,
    user_must_have_access_to_dataset,
)
from lomas_server.admin_database.constants import BudgetDBKey


class AdminYamlDatabase(AdminDatabase):
    """Overall Yaml database management for server state."""

    def __init__(self, yaml_db_path: str) -> None:
        """Load DB from disk.

        Args:
            yaml_db_path (str): path to yaml db file.
        """
        self.path: str = yaml_db_path
        with open(yaml_db_path, mode="r", encoding="utf-8") as f:
            self.database = yaml.safe_load(f)

    def does_user_exist(self, user_name: str) -> bool:
        """Checks if user exist in the database.

        Args:
            user_name (str): name of the user to check

        Returns:
            bool: True if the user exists, False otherwise.
        """
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                return True

        return False

    def does_dataset_exist(self, dataset_name: str) -> bool:
        """Checks if dataset exist in the database.

        Args:
            dataset_name (str): name of the dataset to check

        Returns:
            bool: True if the dataset exists, False otherwise.
        """
        for dt in self.database["datasets"]:
            if dt["dataset_name"] == dataset_name:
                return True

        return False

    @dataset_must_exist
    def get_dataset_metadata(self, dataset_name: str) -> Metadata:
        """Returns the metadata dictionnary of the dataset.

        Wrapped by :py:func:`dataset_must_exist`.

        Args:
            dataset_name (str): name of the dataset to get the metadata

        Returns:
            Metadata: The metadata model.
        """
        for dt in self.database["datasets"]:
            if dt["dataset_name"] == dataset_name:
                metadata_path = dt["metadata_access"]["path"]

                with open(metadata_path, mode="r", encoding="utf-8") as f:
                    metadata = yaml.safe_load(f)

        return Metadata.model_validate(metadata)

    @user_must_exist
    def set_may_user_query(self, user_name: str, may_query: bool) -> None:
        """Sets if a user may query the server.

        (Set False before querying and True after updating budget)

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            may_query (bool): flag give or remove access to user
        """
        users = self.database["users"]
        for user in users:
            if user["user_name"] == user_name:
                user["may_query"] = may_query
        self.database["users"] = users

    @user_must_exist
    def get_and_set_may_user_query(self, user_name: str, may_query: bool) -> bool:
        """
        Atomic operation to check and set if the user may query the server.

        (Set False before querying and True after updating budget)

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            may_query (bool): flag give or remove access to user

        Returns:
            bool: The may_query status of the user before the update.
        """
        previous_may_query = False

        users = self.database["users"]
        new_users = []
        for user in users:
            if user["user_name"] == user_name:
                previous_may_query = user["may_query"]
                user["may_query"] = may_query
                new_users.append(user)
        self.database["users"] = new_users

        return previous_may_query

    @user_must_exist
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        """Checks if a user may access a particular dataset.

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            bool: True if the user has access, False otherwise.
        """
        if not self.does_dataset_exist(dataset_name):
            raise InvalidQueryException(
                f"Dataset {dataset_name} does not exist. "
                + "Please, verify the client object initialisation.",
            )
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                for dataset in user["datasets_list"]:
                    if dataset["dataset_name"] == dataset_name:
                        return True
        return False

    def get_epsilon_or_delta(
        self, user_name: str, dataset_name: str, parameter: BudgetDBKey
    ) -> float:
        """Get total spent epsilon or delta by user on dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (BudgetDBKey): One of BudgetDBKey

        Returns:
            float: The requested budget value.
        """
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                for dataset in user["datasets_list"]:
                    if dataset["dataset_name"] == dataset_name:
                        return dataset[parameter]
        return False

    def update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: str,
        spent_value: float,
    ) -> None:
        """Update current budget spent by user with the last spent budget.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): "current_epsilon" or "current_delta"
            spent_value (float): spending of epsilon or delta on last query
        """
        users = self.database["users"]
        for user in users:
            if user["user_name"] == user_name:
                for dataset in user["datasets_list"]:
                    if dataset["dataset_name"] == dataset_name:
                        dataset[parameter] += spent_value
        self.database["users"] = users

    @dataset_must_exist
    def get_dataset(self, dataset_name: str) -> DSInfo:  # type: ignore[return]
        """
        Get dataset access info based on dataset_name.

        Wrapped by :py:func:`dataset_must_exist`.

        Args:
            dataset_name (str): Name of the dataset.

        Returns:
            Dataset: The dataset model.
        """
        for dt in self.database["datasets"]:
            if dt["dataset_name"] == dataset_name:
                break

        return DSInfo.model_validate(dt)  # pylint: disable=W0631

    @user_must_have_access_to_dataset
    def get_user_previous_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> List[dict]:
        """Retrieves and return the queries already done by a user.

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[dict]: List of previous queries.
        """
        previous_queries = []
        for q in self.database["queries"]:
            if q["user_name"] == user_name and q["dataset_name"] == dataset_name:
                previous_queries.append(q)
        return previous_queries

    def save_query(
        self, user_name: str, query: LomasRequestModel, response: QueryResponse
    ) -> None:
        """Save queries of user on datasets in a separate collection (table).

        Args:
            user_name (str): name of the user
            query (LomasRequestModel): Request object received from client
            response (QueryResponse): Response object sent to client
        """
        to_archive = super().prepare_save_query(user_name, query, response)
        self.database["queries"].append(to_archive)

    def save_current_database(self) -> None:
        """Saves the current database with updated parameters in new yaml."""
        new_path = self.path.replace(
            ".yaml",
            f'_{datetime.now(timezone.utc).strftime("%m_%d_%Y__%H_%M")}.yaml',
        )
        with open(new_path, mode="w", encoding="utf-8") as file:
            yaml.dump(self.database, file)
