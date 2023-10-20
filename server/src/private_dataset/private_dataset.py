from abc import ABC, abstractmethod
import pandas as pd
import shutil

from dataset_store.private_dataset_observer import PrivateDatasetObserver


class PrivateDataset(ABC):
    """
    Overall access to sensitive data
    """

    df = None
    local_path = None
    local_dir = None

    def __init__(self, metadata: dict) -> None:
        """
        Connects to the DB
        Parameters:
            - metadata: The metadata for this dataset
            - **connection_parameters: parameters required to access the db
        """
        self.metadata = metadata
        self.dataset_observers = []

    def __del__(self):
        """
        Cleans up the temporary directory used for storing
        the dataset locally if needed.
        """
        if self.local_dir is not None:
            shutil.rmtree(self.local_dir)

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

    def get_memory_usage(self) -> int:
        """
        Returns the memory usage of this dataset, in MiB.

        The number returned only takes into account the memory usage
        of the pandas DataFrame "cached" in the instance.
        """
        if self.df is None:
            return 0
        else:
            return self.df.memory_usage().sum() / (1024**2)

    def subscribe_for_memory_usage_updates(
        self, dataset_observer: PrivateDatasetObserver
    ):
        """
        Add the PrivateDatasetObserver to the list of dataset_observers.
        """
        self.dataset_observers.append(dataset_observer)
