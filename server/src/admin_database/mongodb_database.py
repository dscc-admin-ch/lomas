import time
from typing import List

from admin_database.admin_database import AdminDatabase
from constants import DPLibraries
from pymongo import MongoClient
from pymongo.database import Database
from utils.error_handler import InternalServerException


class AdminMongoDatabase(AdminDatabase):
    """
    Overall MongoDB database management
    """

    def __init__(self, connection_string: str, database_name: str) -> None:
        """
        Load DB

        Parameters:
            - connection_string: Connection string to the mongodb
            - database_name: Mongodb database name.
        """
        self.db: Database = MongoClient(connection_string)[database_name]

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
        collection_query = self.db.datasets.find({})
        for document in collection_query:
            if document["dataset_name"] == dataset_name:
                return True

        return False

    @AdminDatabase._does_dataset_exist
    def get_dataset_metadata(self, dataset_name: str) -> dict:
        """
        Returns the metadata dictionnary of the dataset
        Parameters:
            - dataset_name: name of the dataset to get the metadata for
        """
        metadatas = self.db.metadata.find_one(
            {dataset_name: {"$exists": True}}
        )
        return metadatas[dataset_name]  # type: ignore

    @AdminDatabase._does_user_exist
    def may_user_query(self, user_name: str) -> bool:
        """
        Checks if a user may query the server.
        Cannot query if already querying.
        Parameters:
            - user_name: name of the user
        """
        user = self.db.users.find_one({"user_name": user_name})
        return user["may_query"]  # type: ignore

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

    @AdminDatabase._does_dataset_exist
    def get_dataset_field(self, dataset_name: str, key: str) -> str:
        """
        Get dataset field type based on dataset name and key
        Parameters:
            - dataset_name: name of the dataset
            - key: name of the field to get
        """
        dataset = self.db.datasets.find_one({"dataset_name": dataset_name})
        return dataset[key]  # type: ignore

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
        queries = self.db.queries_archives.find(
            {
                "user_name": f"{user_name}",
                "dataset_name": f"{dataset_name}",
            },
            {"_id": 0},
        )
        return [q for q in queries]

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
        to_archive = {
            "user_name": user_name,
            "dataset_name": query_json.dataset_name,
            "response": response,
            "timestamp": time.time(),
        }
        match query_json.__class__.__name__:
            case "SNSQLInp":
                to_archive["api"] = DPLibraries.SMARTNOISE_SQL
                to_archive["query"] = query_json.query_str
                to_archive["epsilon_parameter"] = query_json.epsilon
                to_archive["delta_parameter"] = query_json.delta
                to_archive["mechanisms"] = query_json.mechanisms
                to_archive["postprocess"] = query_json.postprocess

            case "OpenDPInp":
                to_archive["api"] = DPLibraries.OPENDP
                to_archive["query"] = query_json.opendp_json
                to_archive["input_data_type"] = query_json.input_data_type
                to_archive["fixed_delta"] = query_json.fixed_delta

            case _:
                raise InternalServerException(
                    f"Unknown query input: {query_json.__class__.__name__}"
                )

        self.db.queries_archives.insert_one(to_archive)
