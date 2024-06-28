from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd
import polars as pl

from dataset_store.private_dataset_observer import PrivateDatasetObserver


class PrivateDataset(ABC):
    """
    Overall access to sensitive data
    """

    df: Optional[pd.DataFrame] = None

    def __init__(self, metadata: dict) -> None:
        """Initializer.

        Args:
            metadata (dict): The metadata for this dataset
        """
        self.metadata: dict = metadata
        self.dataset_observers: List[PrivateDatasetObserver] = []
        self.dtypes: dict = _get_dtypes(metadata)

    @abstractmethod
    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Returns:
            pd.DataFrame: The pandas dataframe for this dataset.
        """

    def get_polars_lf(self, ) -> pl.LazyFrame:
        """TODO: Very inefficient way of doing things. Options are:
            1. always return a lazyframe (scan_csv, not possible with s3)
            2. as is implemented now
            3. cache a dataframe and return a .lazy() version, a bit more efficient
               in speed than 1. but potentially uses double the memory if mixed with
               pandas df.
            4. ??

        Returns:
            pl.LazyFrame: _description_
        """
        return pl.from_pandas(self.get_pandas_df()).lazy()

    def get_metadata(self) -> dict:
        """Get the metadata for this dataset

        Returns:
            dict: The metadata dictionary.
        """
        return self.metadata

    def get_memory_usage(self) -> int:
        """Returns the memory usage of this dataset, in MiB.

        The number returned only takes into account the memory usage
        of the pandas DataFrame "cached" in the instance.

        Returns:
            int: The memory usage, in MiB.
        """
        if self.df is None:
            return 0
        return self.df.memory_usage().sum() / (1024**2)

    def subscribe_for_memory_usage_updates(
        self, dataset_observer: PrivateDatasetObserver
    ) -> None:
        """Add the PrivateDatasetObserver to the list of dataset_observers.

        Args:
            dataset_observer (PrivateDatasetObserver):
                The observer of this dataset.
        """
        self.dataset_observers.append(dataset_observer)


def _get_dtypes(metadata: dict) -> dict:
    """Extract and return the column types from the metadata.

    Args:
        metadata (dict): The metadata dictionary.

    Returns:
        dict: The dictionary of the column type.
    """
    dtypes = {}
    for col_name, data in metadata["columns"].items():
        if data["type"] in ["int", "float"]:
            dtypes[col_name] = f"{data['type']}{data['precision']}"
        else:
            dtypes[col_name] = data["type"]
    
    return dtypes
