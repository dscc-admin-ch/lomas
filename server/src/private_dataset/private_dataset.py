from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd
from dataset_store.private_dataset_observer import PrivateDatasetObserver


class PrivateDataset(ABC):
    """
    Overall access to sensitive data
    """

    df: Optional[pd.DataFrame] = None

    def __init__(self, metadata: dict) -> None:
        """
        Connects to the DB
        Parameters:
            - metadata: The metadata for this dataset
        """
        self.metadata: dict = metadata
        self.dataset_observers: List[PrivateDatasetObserver] = []
        self.dtypes: dict = get_dtypes(metadata)

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
    ) -> None:
        """
        Add the PrivateDatasetObserver to the list of dataset_observers.
        """
        self.dataset_observers.append(dataset_observer)


def get_dtypes(metadata: dict) -> dict:
    dtypes = {}
    for col_name, data in metadata["columns"].items():
        dtypes[col_name] = data["type"]
    return dtypes
