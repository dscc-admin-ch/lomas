from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import pandas as pd
import polars as pl

from dataset_store.private_dataset_observer import PrivateDatasetObserver
from utils.collection_models import Metadata


class PrivateDataset(ABC):
    """
    Overall access to sensitive data
    """

    df: Optional[pd.DataFrame] = None

    def __init__(self, metadata: Metadata) -> None:
        """Initializer.

        Args:
            metadata (Metadata): The metadata for this dataset
        """
        self.metadata: dict = metadata
        self.dataset_observers: List[PrivateDatasetObserver] = []

        dtypes, datetime_columns = get_column_dtypes(metadata)
        self.dtypes: Dict[str, str] = dtypes
        self.datetime_columns: List[str] = datetime_columns

    @abstractmethod
    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Returns:
            pd.DataFrame: The pandas dataframe for this dataset.
        """

    def get_polars_lf(
        self,
    ) -> pl.LazyFrame:
        """Get the data in polars lazyframe format.

        Returns:
            pl.LazyFrame: The polars lazyframe for this dataset.
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


def get_column_dtypes(metadata: dict) -> Tuple[Dict[str, str], List[str]]:
    """Extract and return the column types from the metadata.

    Args:
        metadata (dict): The metadata dictionary.

    Returns:
        dict: The dictionary of the column type.
        list: The list of columns of datetime type
    """
    dtypes = {}
    datetime_columns = []
    for col_name, data in metadata["columns"].items():
        if data["type"] == "datetime":
            dtypes[col_name] = "string"
            datetime_columns.append(col_name)
        else:
            dtypes[col_name] = data["type"]
    return dtypes, datetime_columns
