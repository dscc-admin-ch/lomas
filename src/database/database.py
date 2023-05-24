from abc import ABC, abstractmethod
import functools


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
    def does_user_exists(self, user_name: str) -> bool:
        """
        Checks if user exist in the database
        Parameters:
            - user_name: name of the user to check
        """
        pass
    
    def _does_user_exists(func):
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
            print(f'in decorator, user name {user_name}')
            if not (self.does_user_exists(user_name)):
                raise ValueError(
                    f"User {user_name} does not exists. Cannot continue."
                )
            return func(*args, **kwargs)
        return wrapper_decorator
    
    @abstractmethod
    def does_dataset_exists(self, dataset_name: str) -> bool:
        """
        Checks if dataset exist in the database
        Parameters:
            - dataset_name: name of the dataset to check
        """
        pass

    @abstractmethod
    @_does_user_exists
    def may_user_query(self, user_name: str) -> bool:
        """
        Checks if a user may query the server.
        Cannot query if already querying.
        Parameters:
            - user_name: name of the user
        """
        pass

    @abstractmethod
    @_does_user_exists
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
    @_does_user_exists
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
        def wrapper_decorator(*args, **kwargs) :
            self = args[0]
            user_name = args[1]
            dataset_name = args[2]
            if not self.has_user_access_to_dataset(user_name, dataset_name):
                raise ValueError(
                    f"{user_name} has no access to {dataset_name}. "
                    "Cannot access budget functions."
            )
            return func(*args, **kwargs)
        return wrapper_decorator

    @abstractmethod
    @_has_user_access_to_dataset
    def get_current_budget(
        self, user_name: str, dataset_name: str
    ) -> [float, float]:
        """
        Get the current epsilon and delta spent by a specific user
        on a specific dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        pass

    @abstractmethod
    @_has_user_access_to_dataset
    def get_max_budget(
        self, user_name: str, dataset_name: str
    ) -> [float, float]:
        """
        Get the maximum epsilon and delta budget that can be spent by a user
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        """
        pass

    @abstractmethod
    def update_epsilon(
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
        pass

    @abstractmethod
    def update_delta(
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
        pass

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
