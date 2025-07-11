from abc import ABC, abstractmethod

import pandas as pd
import polars as pl

from lomas_core.models.collections import DatetimeMetadata, Metadata


class DataConnector(ABC):
    """Overall access to sensitive data."""

    df: pd.DataFrame | None = None

    def __init__(self, metadata: Metadata) -> None:
        """Initializer.

        Args:
            metadata (Metadata): The metadata for this dataset
        """
        self.metadata: Metadata = metadata

        dtypes, datetime_columns = get_column_dtypes(self.metadata)
        self.dtypes: dict[str, str] = dtypes
        self.datetime_columns: list[str] = datetime_columns

    @abstractmethod
    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

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

    def get_metadata(self) -> Metadata:
        """Get the metadata for this dataset.

        Returns:
            Metadata: The metadata object.
        """
        return self.metadata


def get_column_dtypes(metadata: Metadata) -> tuple[dict[str, str], list[str]]:
    """Extracts and returns the column types from the metadata.

    Args:
        metadata (Metadata): The metadata.

    Returns:
        Tuple[Dict[str, str], List[str]]:
           dict: The dictionary of the column type.
            list: The list of columns of datetime type
    """

    dtypes = {}
    datetime_columns = []
    for col_name, data in metadata.columns.items():
        if isinstance(data, DatetimeMetadata):
            dtypes[col_name] = "string"
            datetime_columns.append(col_name)
        elif hasattr(data, "precision"):
            dtypes[col_name] = f"{data.type}{data.precision}"
        else:
            dtypes[col_name] = data.type

    return dtypes, datetime_columns
