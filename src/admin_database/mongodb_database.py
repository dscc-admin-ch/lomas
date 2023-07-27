from typing import List
from admin_database.admin_database import AdminDatabase
from utils.constants import ADMIN_DATABASE_NAME
import pymongo


class AdminMongoDatabase(AdminDatabase):
    """
    Overall MongoDB database management
    """

    def __init__(self, connection_string: str) -> None:
        """
        Load DB
        """
        self.db = pymongo.MongoClient(connection_string)[ADMIN_DATABASE_NAME]

    def does_user_exist(self, user_name: str) -> bool:
        """
        Checks if user exist in the database
        Parameters:
            - user_name: name of the user to check
        """
        doc_count = self.db.users.count_documents(
            {"user_name": f"{user_name}"}
        )
        return True if doc_count > 0 else False

    def does_dataset_exist(self, dataset_name: str) -> bool:
        """
        Checks if dataset exist in the database
        Parameters:
            - dataset_name: name of the dataset to check
        """
        doc_count = self.db.metadata.count_documents(
            {dataset_name: {"$exists": True}}
        )
        return doc_count > 0

    @AdminDatabase._does_dataset_exist
    def get_dataset_metadata(self, dataset_name: str) -> dict:
        """
        Returns the metadata dictionnary of the dataset
        Parameters:
            - dataset_name: name of the dataset to get the metadata for
        """
        return self.db.metadata.find_one({dataset_name: {"$exists": True}})[
            dataset_name
        ]

    @AdminDatabase._does_user_exist
    def may_user_query(self, user_name: str) -> bool:
        """
        Checks if a user may query the server.
        Cannot query if already querying.
        Parameters:
            - user_name: name of the user
        """
        return self.db.users.find_one({"user_name": user_name})["may_query"]

    @AdminDatabase._does_user_exist
    def set_may_user_query(self, user_name: str, may_query: bool) -> None:
        """
        Sets if a user may query the server.
        (Set False before querying and True after updating budget)
        Parameters:
            - user_name: name of the user
            - may_query: flag give or remove access to user
        """
        self.db.users.update_one(
            {"user_name": f"{user_name}"},
            {"$set": {"may_query": may_query}},
        )

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
        doc_count = self.db.users.count_documents(
            {
                "user_name": f"{user_name}",
                "datasets_list.dataset_name": f"{dataset_name}",
            }
        )
        return True if doc_count > 0 else False

    def __get_epsilon_or_delta(
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
        return list(
            self.db.users.aggregate(
                [
                    {"$unwind": "$datasets_list"},
                    {
                        "$match": {
                            "user_name": f"{user_name}",
                            "datasets_list.dataset_name": f"{dataset_name}",
                        }
                    },
                ]
            )
        )[0]["datasets_list"][parameter]

    @AdminDatabase._has_user_access_to_dataset
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
                user_name, dataset_name, "total_spent_epsilon"
            ),
            self.__get_epsilon_or_delta(
                user_name, dataset_name, "total_spent_delta"
            ),
        ]

    @AdminDatabase._has_user_access_to_dataset
    def get_initial_budget(
        self, user_name: str, dataset_name: str
    ) -> List[float]:
        """
        Get the inital epsilon and delta budget
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        return [
            self.__get_epsilon_or_delta(
                user_name, dataset_name, "initial_epsilon"
            ),
            self.__get_epsilon_or_delta(
                user_name, dataset_name, "initial_delta"
            ),
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
        self.db.users.update_one(
            {
                "user_name": f"{user_name}",
                "datasets_list.dataset_name": f"{dataset_name}",
            },
            {"$inc": {f"datasets_list.$.{parameter}": spent_value}},
        )

    def __update_epsilon(
        self, user_name: str, dataset_name: str, spent_epsilon: float
    ) -> None:
        """
        Update the spent epsilon by a specific user
        with the total spent epsilon
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_epsilon: value of epsilon spent on last query
        """
        return self.__update_epsilon_or_delta(
            user_name, dataset_name, "total_spent_epsilon", spent_epsilon
        )

    def __update_delta(
        self, user_name: str, dataset_name: str, spent_delta: float
    ) -> None:
        """
        Update the spent delta spent by a specific user
        with the total spent delta of the user
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_delta: value of delta spent on last query
        """
        self.__update_epsilon_or_delta(
            user_name, dataset_name, "total_spent_delta", spent_delta
        )

    @AdminDatabase._has_user_access_to_dataset
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
        Save queries of user on datasets in a separate collection (table)
        named "queries_archives" in the DB
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - epsilon: value of epsilon spent on last query
            - delta: value of delta spent on last query
            - query: json string of the query
        """
        self.db.queries_archives.insert_one(
            {
                "user_name": f"{user_name}",
                "dataset_name": f"{dataset_name}",
                "epsilon": epsilon,
                "delta": delta,
                "query": query,
            }
        )
