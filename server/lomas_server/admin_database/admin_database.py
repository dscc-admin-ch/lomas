import argparse
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, Dict, List

from lomas_core.error_handler import (
    InvalidQueryException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import DSInfo, Metadata
from lomas_core.models.requests import LomasRequestModel, model_input_to_lib
from lomas_core.models.responses import QueryResponse

from lomas_server.admin_database.constants import BudgetDBKey


def user_must_exist(func: Callable) -> Callable:  # type: ignore
    """
    Decorator function to verify that a user exists.

    Args:
        func (Callable): Function to be decorated.
            Wrapped function arguments must include:
            - args[0] (str): username

    Raises:
        UnauthorizedAccessException: If the user does not exist.

    Returns:
        Callable: Wrapper function that verifies the user exists
            before calling func.
    """

    @wraps(func)
    def wrapper_decorator(
        self, *args: argparse.Namespace, **kwargs: Dict[str, str]
    ) -> None:
        user_name = args[0]
        if not self.does_user_exist(user_name):
            raise UnauthorizedAccessException(
                f"User {user_name} does not exist. "
                + "Please, verify the client object initialisation.",
            )
        return func(self, *args, **kwargs)

    return wrapper_decorator


def dataset_must_exist(func: Callable) -> Callable:  # type: ignore
    """
    Decorator function to verify that a dataset exists.

    Args:
        func (Callable): Function to be decorated.
            Wrapped function arguments must include:
            - args[0] (str): dataset name

    Raises:
        InvalidQueryException: If the dataset does not exist.

    Returns:
        Callable: Wrapper function that checks if the dataset exists
            before calling the wrapped function.
    """

    @wraps(func)
    def wrapper_decorator(
        self, *args: argparse.Namespace, **kwargs: Dict[str, str]
    ) -> None:
        dataset_name = args[0]
        if not self.does_dataset_exist(dataset_name):
            raise InvalidQueryException(
                f"Dataset {dataset_name} does not exist. "
                + "Please, verify the client object initialisation.",
            )
        return func(self, *args, **kwargs)

    return wrapper_decorator


def user_must_have_access_to_dataset(
    func: Callable,
) -> Callable:  # type: ignore
    """
    Decorator function to enforce a user has access to a dataset.

    Args:
        func (Callable): Function to be decorated.
            Wrapped function arguments must include:
            - args[0] (str): user name
            - args[1] (str): dataset name

    Raises:
        UnauthorizedAccessException: If the user does not have
            access to the dataset.

    Returns:
        Callable: Wrapper function that checks if the user has access
            to the dataset before calling the wrapped function.
    """

    @wraps(func)
    def wrapper_decorator(
        self, *args: argparse.Namespace, **kwargs: Dict[str, str]
    ) -> None:
        user_name = args[0]
        dataset_name = args[1]
        if not self.has_user_access_to_dataset(user_name, dataset_name):
            raise UnauthorizedAccessException(
                f"{user_name} does not have access to {dataset_name}.",
            )
        return func(self, *args, **kwargs)

    return wrapper_decorator


class AdminDatabase(ABC):
    """Overall database management for server state."""

    @abstractmethod
    def __init__(self, **connection_parameters: Dict[str, str]) -> None:
        """
        Connects to the DB.

        Args:
            **connection_parameters (Dict[str, str]): parameters required
                to access the db
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
    def does_dataset_exist(self, dataset_name: str) -> bool:
        """
        Checks if dataset exist in the database.

        Args:
            dataset_name (str): name of the dataset to check

        Returns:
            bool: True if the dataset exists, False otherwise.
        """

    @abstractmethod
    @dataset_must_exist
    @user_must_have_access_to_dataset
    def get_dataset_metadata(self, dataset_name: str) -> Metadata:
        """
        Returns the metadata dictionnary of the dataset.

        Wrapped by :py:func:`dataset_must_exist`.

        Args:
            dataset_name (str): name of the dataset to get the metadata

        Returns:
            Metadata: The metadata object.
        """

    @abstractmethod
    @user_must_exist
    def set_may_user_query(self, user_name: str, may_query: bool) -> bool:
        """
        Sets if a user may query the server..

        (Set False before querying and True after updating budget)

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            may_query (bool): flag give or remove access to user
        """

    @abstractmethod
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

    @abstractmethod
    @user_must_exist
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        """
        Checks if a user may access a particular dataset.

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            bool: True if the user has access, False otherwise.
        """

    @abstractmethod
    def get_epsilon_or_delta(
        self, user_name: str, dataset_name: str, parameter: BudgetDBKey
    ) -> float:
        """
        Get the total spent epsilon or delta by user on dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): Member of BudgetDBKey.

        Returns:
            float: The requested budget value.
        """

    @user_must_have_access_to_dataset
    def get_total_spent_budget(self, user_name: str, dataset_name: str) -> List[float]:
        """
        Get the total spent epsilon and delta spent by user on dataset.

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[float]: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return [
            self.get_epsilon_or_delta(
                user_name, dataset_name, BudgetDBKey.EPSILON_SPENT
            ),
            self.get_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.DELTA_SPENT),
        ]

    @user_must_have_access_to_dataset
    def get_initial_budget(self, user_name: str, dataset_name: str) -> List[float]:
        """
        Get the initial epsilon and delta budget.

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[float]: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return [
            self.get_epsilon_or_delta(
                user_name, dataset_name, BudgetDBKey.EPSILON_INIT
            ),
            self.get_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.DELTA_INIT),
        ]

    @user_must_have_access_to_dataset
    def get_remaining_budget(self, user_name: str, dataset_name: str) -> List[float]:
        """
        Get the remaining epsilon and delta budget (initial - total spent).

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[float]: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        init_eps, init_delta = self.get_initial_budget(user_name, dataset_name)
        spent_eps, spent_delta = self.get_total_spent_budget(user_name, dataset_name)
        return [init_eps - spent_eps, init_delta - spent_delta]

    @abstractmethod
    def update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        spent_value: float,
    ) -> None:
        """
        Update current budget spent by user with spent budget.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): One of BudgetDBKey
            spent_value (float): spending of epsilon or delta on last query
        """

    def update_epsilon(
        self, user_name: str, dataset_name: str, spent_epsilon: float
    ) -> None:
        """
        Update spent epsilon by user with total spent epsilon.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            spent_epsilon (float): value of epsilon spent on last query
        """
        return self.update_epsilon_or_delta(
            user_name, dataset_name, BudgetDBKey.EPSILON_SPENT, spent_epsilon
        )

    def update_delta(
        self, user_name: str, dataset_name: str, spent_delta: float
    ) -> None:
        """
        Update spent delta spent by user with spent delta of the user.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            spent_delta (float): value of delta spent on last query
        """
        self.update_epsilon_or_delta(
            user_name, dataset_name, BudgetDBKey.DELTA_SPENT, spent_delta
        )

    @user_must_have_access_to_dataset
    def update_budget(
        self,
        user_name: str,
        dataset_name: str,
        spent_epsilon: float,
        spent_delta: float,
    ) -> None:
        """
        Update current epsilon and delta delta spent by user.

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            spent_epsilon (float): value of epsilon spent on last query
            spent_delta (float): value of delta spent on last query
        """
        self.update_epsilon(user_name, dataset_name, spent_epsilon)
        self.update_delta(user_name, dataset_name, spent_delta)

    @abstractmethod
    @dataset_must_exist
    def get_dataset(self, dataset_name: str) -> DSInfo:
        """
        Get dataset access info based on dataset_name.

        Wrapped by :py:func:`dataset_must_exist`.

        Args:
            dataset_name (str): Name of the dataset.

        Returns:
            Dataset: The dataset model.
        """

    @abstractmethod
    @user_must_have_access_to_dataset
    def get_user_previous_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> List[dict]:
        """
        Retrieves and return the queries already done by a user.

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[dict]: List of previous queries.
        """

    def prepare_save_query(
        self, user_name: str, query: LomasRequestModel, response: QueryResponse
    ) -> dict:
        """
        Prepare the query to save in archives.

        Args:
            user_name (str): name of the user
            query (LomasRequestModel): Request object received from client
            response (QueryResponse): Response object sent to client

        Raises:
            InternalServerException: If the type of query is unknown.

        Returns:
            dict: The query archive dictionary.
        """
        to_archive = {
            "user_name": user_name,
            "dataset_name": query.dataset_name,
            "dp_librairy": model_input_to_lib(query),
            "client_input": query.model_dump(),
            "response": response.model_dump(),
            "timestamp": time.time(),
        }  # TODO 359 use model for that one too.

        return to_archive

    @abstractmethod
    def save_query(
        self, user_name: str, query: LomasRequestModel, response: QueryResponse
    ) -> None:
        """
        Save queries of user on datasets in a separate collection (table).

        Args:
            user_name (str): name of the user
            query (LomasRequestModel): Request object received from client
            response (QueryResponse): Response object sent to client
        """
