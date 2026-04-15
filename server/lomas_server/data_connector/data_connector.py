from abc import ABC, abstractmethod
from typing import Annotated

import pandas as pd
import polars as pl
from csvw_safe.datatypes import XSD_GROUP_MAP, DataTypesGroups, to_pandas_dtype
from csvw_safe.metadata_structure import TableMetadata
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
)

from lomas_core.models.utils import dataframe_to_dict


class DataConnector(BaseModel, ABC):
    """Overall access to sensitive data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: TableMetadata

    df: Annotated[pd.DataFrame | None, Field(exclude=True), PlainSerializer(dataframe_to_dict)] = None

    @property
    def dtypes(self) -> dict[str, str]:
        return {
            col.name: to_pandas_dtype(col.datatype)
            for col in self.metadata.columns
            if XSD_GROUP_MAP[col.datatype] != DataTypesGroups.DATETIME
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def datetime_columns(self) -> list[str]:
        return [
            col.name
            for col in self.metadata.columns
            if XSD_GROUP_MAP[col.datatype] == DataTypesGroups.DATETIME
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
