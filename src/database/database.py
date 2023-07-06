from abc import ABC, abstractmethod
import functools
from typing import List
from fastapi import HTTPException


class Database(ABC):
    """
    Overall database management while server is running
    """

    @abstractmethod
    def __init__(self, **connection_parameters) -> None:
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

    def _does_user_exist(func):
        """
        Decorator function to check if a user exists
        Parameters:
            - args[0]: expects self
            - args[1]: expects username
        """

        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            self = args[0]
            user_name = args[1]
            if not (self.does_user_exist(user_name)):
                raise HTTPException(404, f"User {user_name} does not exist.")
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

    def _does_dataset_exist(func):
        """
        Decorator function to check if a user exists
        Parameters:
            - args[0]: expects self
            - args[1]: expects username
        """

        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            self = args[0]
            dataset_name = args[1]
            if not (self.does_dataset_exist(dataset_name)):
                raise HTTPException(
                    404, f"Dataset {dataset_name} does not exists."
                )
            return func(*args, **kwargs)

        return wrapper_decorator

    @abstractmethod
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

    def _has_user_access_to_dataset(func):
        """
        Decorator function to check if a user has access to a dataset
        Parameters:
            - args[0]: expects self
            - args[1]: expects username
            - args[2]: expects dataset_name
        """

        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            self = args[0]
            user_name = args[1]
            dataset_name = args[2]
            if not self.has_user_access_to_dataset(user_name, dataset_name):
                raise HTTPException(
                    404, f"{user_name} does not have access to {dataset_name}."
                )
            return func(*args, **kwargs)

        return wrapper_decorator

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

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
        pass

    @abstractmethod
    def save_query(
        self,
        user_name: str,
        dataset_name: str,
        epsilon: float,
        delta: float,
        query: dict,
    ) -> None:
        """
        Save queries of user on datasets in a separate (part of) db
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - epsilon: value of epsilon spent on last query
            - delta: value of delta spent on last query
            - query: json string of the query
        """
        pass
