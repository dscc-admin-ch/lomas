import argparse
import functools
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, List

from constants import DPLibraries
from utils.error_handler import (
    InvalidQueryException,
    UnauthorizedAccessException,
    InternalServerException,
)


class AdminDatabase(ABC):
    """
    Overall database management while server is running
    """

    @abstractmethod
    def __init__(self, **connection_parameters: Dict[str, str]) -> None:
        """
        Connects to the DB
        Parameters:
            - **connection_parameters: parameters required to access the db
        """
        pass

    @abstractmethod
    def does_user_exist(self, user_name: str) -> bool:
        """
        Checks if user exist in the database
        Parameters:
            - user_name: name of the user to check
        """
        pass

    def _does_user_exist(func: Callable) -> Callable:
        """
        Decorator function to check if a user exists
        Parameters:
            - args[0]: expects self
            - args[1]: expects username
        """

        @functools.wraps(func)
        def wrapper_decorator(
            *args: argparse.Namespace, **kwargs: Dict[str, str]
        ) -> None:
            self = args[0]
            user_name = args[1]
            if not (self.does_user_exist(user_name)):
                raise UnauthorizedAccessException(
                    f"User {user_name} does not exist. "
                    + "Please, verify the client object initialisation.",
                )
            return func(*args, **kwargs)

        return wrapper_decorator

    @abstractmethod
    def does_dataset_exist(self, dataset_name: str) -> bool:
        """
        Checks if dataset exist in the database
        Parameters:
            - dataset_name: name of the dataset to check
        """
        pass

    def _does_dataset_exist(func: Callable) -> Callable:
        """
        Decorator function to check if a user exists
        Parameters:
            - args[0]: expects self
            - args[1]: expects username
        """

        @functools.wraps(func)
        def wrapper_decorator(
            *args: argparse.Namespace, **kwargs: Dict[str, str]
        ) -> None:
            self = args[0]
            dataset_name = args[1]
            if not (self.does_dataset_exist(dataset_name)):
                raise InvalidQueryException(
                    f"Dataset {dataset_name} does not exists. "
                    + "Please, verify the client object initialisation.",
                )
            return func(*args, **kwargs)

        return wrapper_decorator

    @abstractmethod
    @_does_dataset_exist
    def get_dataset_metadata(self, dataset_name: str) -> dict:
        """
        Returns the metadata dictionnary of the dataset
        Parameters:
            - dataset_name: name of the dataset to get the metadata for
        """
        pass

    @abstractmethod
    @_does_user_exist
    def may_user_query(self, user_name: str) -> bool:
        """
        Checks if a user may query the server.
        Cannot query if already querying.
        Parameters:
            - user_name: name of the user
        """
        pass

    @abstractmethod
    @_does_user_exist
    def set_may_user_query(self, user_name: str, may_query: bool) -> None:
        """
        Sets if a user may query the server.
        (Set False before querying and True after updating budget)
        Parameters:
            - user_name: name of the user
            - may_query: flag give or remove access to user
        """
        pass

    @abstractmethod
    @_does_user_exist
    def has_user_access_to_dataset(
        self, user_name: str, dataset_name: str
    ) -> bool:
        """
        Checks if a user may access a particular dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        pass

    def _has_user_access_to_dataset(func: Callable) -> Callable:
        """
        Decorator function to check if a user has access to a dataset
        Parameters:
            - args[0]: expects self
            - args[1]: expects username
            - args[2]: expects dataset_name
        """

        @functools.wraps(func)
        def wrapper_decorator(
            *args: argparse.Namespace, **kwargs: Dict[str, str]
        ) -> None:
            self = args[0]
            user_name = args[1]
            dataset_name = args[2]
            if not self.has_user_access_to_dataset(user_name, dataset_name):
                raise UnauthorizedAccessException(
                    f"{user_name} does not have access to {dataset_name}.",
                )
            return func(*args, **kwargs)

        return wrapper_decorator

    @abstractmethod
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
        pass

    @_has_user_access_to_dataset
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
            self.get_epsilon_or_delta(
                user_name, dataset_name, "total_spent_epsilon"
            ),
            self.get_epsilon_or_delta(
                user_name, dataset_name, "total_spent_delta"
            ),
        ]

    @_has_user_access_to_dataset
    def get_initial_budget(
        self, user_name: str, dataset_name: str
    ) -> List[float]:
        """
        Get the initial epsilon and delta budget
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        return [
            self.get_epsilon_or_delta(
                user_name, dataset_name, "initial_epsilon"
            ),
            self.get_epsilon_or_delta(
                user_name, dataset_name, "initial_delta"
            ),
        ]

    @_has_user_access_to_dataset
    def get_remaining_budget(
        self, user_name: str, dataset_name: str
    ) -> List[float]:
        """
        Get the remaining epsilon and delta budget (initial - total spent)
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        init_eps, init_delta = self.get_initial_budget(user_name, dataset_name)
        spent_eps, spent_delta = self.get_total_spent_budget(
            user_name, dataset_name
        )
        return [init_eps - spent_eps, init_delta - spent_delta]

    @abstractmethod
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
        pass

    def update_epsilon(
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
        return self.update_epsilon_or_delta(
            user_name, dataset_name, "total_spent_epsilon", spent_epsilon
        )

    def update_delta(
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
        self.update_epsilon_or_delta(
            user_name, dataset_name, "total_spent_delta", spent_delta
        )

    @_has_user_access_to_dataset
    def update_budget(
        self,
        user_name: str,
        dataset_name: str,
        spent_epsilon: float,
        spent_delta: float,
    ) -> None:
        """
        Update the current epsilon and delta spent by a specific user
        with the last spent delta
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_epsilon: value of epsilon spent on last query
            - spent_delta: value of delta spent on last query
        """
        self.update_epsilon(user_name, dataset_name, spent_epsilon)
        self.update_delta(user_name, dataset_name, spent_delta)

    @abstractmethod
    @_does_dataset_exist
    def get_dataset_field(self, dataset_name: str, key: str) -> str:
        """
        Get dataset field type based on dataset name and key
        """
        pass

    @abstractmethod
    @_has_user_access_to_dataset
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
        pass

    def prepare_save_query(
        self, user_name: str, query_json: dict, response: dict
    ) -> dict:
        """
        Prepare the query to save in archives
        Parameters:
            - user_name: name of the user
            - query_json: json received from client
            - response: response sent to the client
        """
        to_archive = {
            "user_name": user_name,
            "dataset_name": query_json.dataset_name,
            "client_input": query_json.dict(),
            "response": response,
            "timestamp": time.time(),
        }
        match query_json.__class__.__name__:
            case "SNSQLInp":
                to_archive["dp_librairy"] = DPLibraries.SMARTNOISE_SQL
            case "OpenDPInp":
                to_archive["dp_librairy"] = DPLibraries.OPENDP
            case _:
                raise InternalServerException(
                    f"Unknown query input: {query_json.__class__.__name__}"
                )
        return to_archive

    @abstractmethod
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
        pass
