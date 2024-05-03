from datetime import datetime
import yaml
from typing import List

from admin_database.admin_database import AdminDatabase


class AdminYamlDatabase(AdminDatabase):
    """
    Overall MongoDB database management
    """

    def __init__(self, yaml_db_path: str) -> None:
        """
        Load DB

        Parameters:
            - connection_string: Connection string to the mongodb
            - database_name: Mongodb database name.
        """
        self.path: str = yaml_db_path
        with open(yaml_db_path, "r") as f:
            self.database = yaml.safe_load(f)

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
        for dt in self.database["datasets"]:
            if dt["dataset_name"] == dataset_name:
                return True

        return False

    @AdminDatabase._does_dataset_exist
    def get_dataset_metadata(self, dataset_name: str) -> dict:
        """
        Returns the metadata dictionnary of the dataset
        Parameters:
            - dataset_name: name of the dataset to get the metadata for
        """
        for dt in self.database["datasets"]:
            if dt["dataset_name"] == dataset_name:
                metadata_path = dt["metadata"]["metadata_path"]

        with open(metadata_path, "r") as f:
            metadata = yaml.safe_load(f)

        return metadata

    @AdminDatabase._does_user_exist
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
        # if user not found, return false
        return False

    @AdminDatabase._does_user_exist
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

    @AdminDatabase._does_user_exist
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

    def get_epsilon_or_delta(
        self, user_name: str, dataset_name: str, parameter: str
    ) -> float:
        """
        Get the total spent epsilon or delta  by a specific user
        on a specific dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - parameter: total_spent_epsilon or total_spent_delta
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

    @AdminDatabase._does_dataset_exist
    def get_dataset_field(
        self, dataset_name: str, key: str
    ) -> str:  # type: ignore
        """
        Get dataset field type based on dataset name and key
        Parameters:
            - dataset_name: name of the dataset
            - key: name of the field to get
        """
        for dt in self.database["datasets"]:
            if dt["dataset_name"] == dataset_name:
                return dt[key]

    @AdminDatabase._has_user_access_to_dataset
    def get_user_previous_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> List[dict]:
        """
        Retrieves and return the queries already done by a user
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        previous_queries = []
        for q in self.database["queries"]:
            if (
                q["user_name"] == user_name
                and q["dataset_name"] == dataset_name
            ):
                previous_queries.append(q)
        return previous_queries

    def save_query(
        self, user_name: str, query_json: dict, response: dict
    ) -> None:
        """
        Save queries of user on datasets in a separate collection (table)
        named "queries_archives" in the DB
        Parameters:
            - user_name: name of the user
            - query_json: json received from client
            - response: response sent to the client
        """
        to_archive = super().prepare_save_query(
            user_name, query_json, response
        )
        self.database["queries"].append(to_archive)

    def save_current_database(self) -> None:
        """
        Saves the current database with updated parameters in new yaml
        with the date and hour in the path
        Might be useful to verify state of DB during development
        """
        new_path = self.path.replace(
            ".yaml", f'_{datetime.now().strftime("%m_%d_%Y__%H_%M_%S")}.yaml'
        )
        with open(new_path, "w") as file:
            yaml.dump(self.database, file)
