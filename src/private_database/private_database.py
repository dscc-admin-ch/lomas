from abc import ABC, abstractmethod
import pandas as pd


class PrivateDatabase(ABC):
    """
    Overall access to sensitive data
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
    def get_csv_path(self) -> str:
        """
        Get the path to the local csv data
        Returns:
            - path
        """
        pass

    @abstractmethod
    def get_pandas_df(self, dataset_name: str) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Parameters:
            - dataset_name: name of the private dataset
        """
        pass
