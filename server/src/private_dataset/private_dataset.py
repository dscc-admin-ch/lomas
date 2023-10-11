from abc import ABC, abstractmethod
import pandas as pd


class PrivateDataset(ABC):
    """
    Overall access to sensitive data
    """

    def __init__(self, metadata, **connection_parameters) -> None:
        """
        Connects to the DB
        Parameters:
            - metadata: The metadata for this dataset
            - **connection_parameters: parameters required to access the db
        """
        self.metadata = metadata

    @abstractmethod
    def get_local_path(self) -> str:
        """
        Get the path to  a local copy of the file.
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

    def get_metadata(self) -> dict:
        """
        Get the metadata for this dataset
        """
        return self.metadata
