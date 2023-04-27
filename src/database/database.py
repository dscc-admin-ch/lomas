from abc import ABC, abstractmethod


class Database(ABC):
    '''
    Overall database management
    '''
    @abstractmethod
    def __init__(self, **connection_parameters):
        '''
        Connects to the DB
        Parameters:
            - **connection_parameters: parameters required to access the db
        '''
        pass
    

    @abstractmethod
    def add_users(self, user_name: str):
        '''
        Adds a user to the database.
        Parameters:
            - user_name: name of the user to add
        '''
        pass


    @abstractmethod
    def remove_users(self, user_name: str):
        '''
        Removes a user from the database.
        Parameters:
            - user_name: name of the user to remove
        '''
        pass


    @abstractmethod
    def does_user_exists(self, user_name: str):
        '''
        Checks if user exist in the database
        Parameters:
            - user_name: name of the user to check
        '''
        pass


    @abstractmethod
    def does_dataset_exists(self, dataset_name: str):
        '''
        Checks if dataset exist in the database
        Parameters:
            - dataset_name: name of the dataset to check
        '''
        pass


    @abstractmethod
    def add_dataset_access_to_user(self, user_name: str, dataset_name: str):
        '''
        Gives dataset access to an existing user
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def remove_dataset_access_to_user(self, user_name: str, dataset_name: str):
        '''
        Removes dataset access to an existing user
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str):
        '''
        Checks if a user may access a particular dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass

    
    @abstractmethod
    def set_max_epsilon(self, user_name: str, dataset_name: str, epsilon: float):
        '''
        Sets maximum epsilon that a user can spend on a dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def set_max_delta(self, user_name: str, dataset_name: str, delta: float):
        '''
        Sets maximum delta that a user can spend on a dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def get_epsilon(self, user_name: str, dataset_name: str):
        '''
        Get the current epsilon spent by a specific user
        on a specific dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def get_delta(self, user_name: str, dataset_name: str):
        '''
        Get the current delta spent by a specific user
        on a specific dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def get_budget(self, user_name: str, dataset_name: str):
        '''
        Get the current epsilon and delta spent by a specific user
        on a specific dataset
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
        '''
        pass


    @abstractmethod
    def update_epsilon(self, user_name: str, dataset_name: str, spent_epsilon: float):
        '''
        Update the current epsilon spent by a specific user 
        with the last spent epsilon
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_epsilon: value of epsilon spent on last query
        '''
        pass


    @abstractmethod
    def update_delta(self, user_name: str, dataset_name: str, spent_delta: float):
        '''
        Update the current delta spent by a specific user 
        with the last spent delta
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - spent_delta: value of delta spent on last query
        '''
        pass

    @abstractmethod
    def save_query(self, user_name: str, dataset_name: str, epsilon: float, delta: float, query: dict):
        '''
        (Optional)
        Save queries of user on datasets in a separate (part of) db
        Parameters:
            - user_name: name of the user
            - dataset_name: name of the dataset
            - epsilon: value of epsilon spent on last query
            - delta: value of delta spent on last query
            - query: json string of the query
        '''
        pass
