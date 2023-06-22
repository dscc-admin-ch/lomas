from datetime import datetime
import json
from typing import List
import yaml

from database.database import Database
from utils.constants import QUERIES_ARCHIVES, DATASET_METADATA_PATHS


class YamlDatabase(Database):
    """
    Overall yaml in memory database management
    """

    def __init__(self, yaml_db_path) -> None:
        """
        Load DB
        """
        self.path = yaml_db_path
        with open(yaml_db_path, "r") as f:
            self.database = yaml.safe_load(f)
        self.queries_archives = []

    def does_user_exist(self, user_name: str) -> bool:
        """
        Checks if user exist in the database
        Parameters:
            - user_name: name of the user to check
        """
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                return True

        return False

    def does_dataset_exist(self, dataset_name: str) -> bool:
        """
        Checks if dataset exist in the database
        Parameters:
            - dataset_name: name of the dataset to check
        """
        return dataset_name in self.database["datasets"]

    @Database._does_dataset_exist
    def get_dataset_metadata(self, dataset_name: str) -> dict:
        ds_metadata_path = DATASET_METADATA_PATHS[dataset_name]

        with open(ds_metadata_path, "r") as f:
            ds_metadata = yaml.safe_load(f)

        return ds_metadata

    @Database._does_user_exist
    def may_user_query(self, user_name: str) -> bool:
        """
        Checks if a user may query the server.
        Cannot query if already querying.
        Parameters:
            - user_name: name of the user
        """
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                return user["may_query"]

    @Database._does_user_exist
    def set_may_user_query(self, user_name: str, may_query: bool) -> None:
        """
        Sets if a user may query the server.
        (Set False before querying and True after updating budget)
        Parameters:
            - user_name: name of the user
            - may_query: flag give or remove access to user
        """
        users = self.database["users"]
        for user in users:
            if user["user_name"] == user_name:
                user["may_query"] = may_query
        self.database["users"] = users

    @Database._does_user_exist
    def has_user_access_to_dataset(
        self, user_name: str, dataset_name: str
    ) -> bool:
        """
        Checks if a user may access a particular dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                for dataset in user["datasets_list"]:
                    if dataset["dataset_name"] == dataset_name:
                        return True
        return False

    def __get_epsilon_or_delta(
        self, user_name: str, dataset_name: str, parameter: str
    ) -> float:
        """
        Get the current epsilon or delta spent by a specific user
        on a specific dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - parameter: current_epsilon or current_delta
        """
        for user in self.database["users"]:
            if user["user_name"] == user_name:
                for dataset in user["datasets_list"]:
                    if dataset["dataset_name"] == dataset_name:
                        return dataset[parameter]

    @Database._has_user_access_to_dataset
    def get_total_spent_budget(
        self, user_name: str, dataset_name: str
    ) -> List[float]:
        """
        Get the total spent epsilon and delta spent by a specific user
        on a specific dataset (since the initialisation)
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        return [
            self.__get_epsilon_or_delta(
                user_name, dataset_name, "current_epsilon"
            ),
            self.__get_epsilon_or_delta(
                user_name, dataset_name, "current_delta"
            ),
        ]

    @Database._has_user_access_to_dataset
    def get_max_budget(
        self, user_name: str, dataset_name: str
    ) -> List[float]:
        """
        Get the maximum epsilon and delta budget that can be spent by a user
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        return [
            self.__get_epsilon_or_delta(
                user_name, dataset_name, "max_epsilon"
            ),
            self.__get_epsilon_or_delta(user_name, dataset_name, "max_delta"),
        ]

    def __update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: str,
        spent_value: float,
    ) -> None:
        """
        Update the current epsilon spent by a specific user
        with the last spent epsilon
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - parameter: current_epsilon or current_delta
            - spent_value: spending of epsilon or delta on last query
        """
        users = self.database["users"]
        for user in users:
            if user["user_name"] == user_name:
                for dataset in user["datasets_list"]:
                    if dataset["dataset_name"] == dataset_name:
                        dataset[parameter] += spent_value
        self.database["users"] = users

    def __update_epsilon(
        self, user_name: str, dataset_name: str, spent_epsilon: float
    ) -> None:
        """
        Update the current epsilon spent by a specific user
        with the last spent epsilon
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_epsilon: value of epsilon spent on last query
        """
        return self.__update_epsilon_or_delta(
            user_name, dataset_name, "current_epsilon", spent_epsilon
        )

    def __update_delta(
        self, user_name: str, dataset_name: str, spent_delta: float
    ) -> None:
        """
        Update the current delta spent by a specific user
        with the last spent delta
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_delta: value of delta spent on last query
        """
        self.__update_epsilon_or_delta(
            user_name, dataset_name, "current_delta", spent_delta
        )

    @Database._has_user_access_to_dataset
    def update_budget(
        self,
        user_name: str,
        dataset_name: str,
        spent_epsilon: float,
        spent_delta: float,
    ) -> None:
        """
        Update the current epsilon and delta spent by a specific user
        with the last spent budget
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_epsilon: value of epsilon spent on last query
            - spent_delta: value of delta spent on last query
        """
        self.__update_epsilon(user_name, dataset_name, spent_epsilon)
        self.__update_delta(user_name, dataset_name, spent_delta)

    def save_query(
        self,
        user_name: str,
        dataset_name: str,
        epsilon: float,
        delta: float,
        query: dict,
    ) -> None:
        """
        Save queries of user on datasets in a separate json file
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - epsilon: value of epsilon spent on last query
            - delta: value of delta spent on last query
            - query: json string of the query
        """
        self.queries_archives.append(
            {
                "user_name": user_name,
                "dataset_name": dataset_name,
                "epsilon": epsilon,
                "delta": delta,
                "query": query,
            }
        )

    def save_current_database(self) -> None:
        """
        Saves the current database with updated parameters in new yaml
        with the date and hour in the path
        Might be useful to verify state of DB during development
        """
        new_path = self.path.replace(
            ".yaml", f'{datetime.now().strftime("%m_%d_%Y__%H_%M_%S")}.yaml'
        )
        with open(new_path, "w") as file:
            yaml.dump(self.database, file)

    def save_current_archive_queries(self) -> None:
        """
        Saves the current list of queries in a JSON
        """
        with open(QUERIES_ARCHIVES, "w") as outfile:
            json.dump(self.queries_archives, outfile)
