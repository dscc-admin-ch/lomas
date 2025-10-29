from abc import ABC, abstractmethod
from typing import Annotated

import pandas as pd
import polars as pl
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
)

from lomas_core.models.collections import DatetimeMetadata, Metadata
from lomas_core.models.utils import (
    dataframe_to_dict,
)


class DataConnector(BaseModel, ABC):
    """Overall access to sensitive data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata

    df: Annotated[pd.DataFrame, PlainSerializer(dataframe_to_dict)] | None = Field(exclude=True, default=None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dtypes(self) -> dict[str, str]:
        dtypes = {}
        for col_name, data in self.metadata.columns.items():
            if isinstance(data, DatetimeMetadata):
                dtypes[col_name] = "string"
            elif hasattr(data, "precision"):
                dtypes[col_name] = f"{data.type}{data.precision}"
            else:
                dtypes[col_name] = data.type

        return dtypes

    @computed_field  # type: ignore[prop-decorator]
    @property
    def datetime_columns(self) -> list[str]:
        return [
            col_name for col_name, data in self.metadata.columns.items() if isinstance(data, DatetimeMetadata)
        ]

    @abstractmethod
    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Returns:
            pd.DataFrame: The pandas dataframe for this dataset.
        """

    def get_polars_lf(self) -> pl.LazyFrame:
        """Get the data in polars lazyframe format.

        Returns:
            pl.LazyFrame: The polars lazyframe for this dataset.
        """
        return pl.from_pandas(self.get_pandas_df()).lazy()


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
