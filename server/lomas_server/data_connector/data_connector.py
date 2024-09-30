from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import pandas as pd
from lomas_core.models.collections import DatetimeMetadata, Metadata


class DataConnector(ABC):
    """Overall access to sensitive data."""

    df: Optional[pd.DataFrame] = None

    def __init__(self, metadata: Metadata) -> None:
        """Initializer.

        Args:
            metadata (Metadata): The metadata for this dataset
        """
        self.metadata: Metadata = metadata

        dtypes, datetime_columns = get_column_dtypes(self.metadata)
        self.dtypes: Dict[str, str] = dtypes
        self.datetime_columns: List[str] = datetime_columns

    @abstractmethod
    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Returns:
            pd.DataFrame: The pandas dataframe for this dataset.
        """

    def get_metadata(self) -> Metadata:
        """Get the metadata for this dataset.

        Returns:
            Metadata: The metadata object.
        """
        return self.metadata


def get_column_dtypes(metadata: Metadata) -> Tuple[Dict[str, str], List[str]]:
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
        else:
            dtypes[col_name] = data.type
    return dtypes, datetime_columns
