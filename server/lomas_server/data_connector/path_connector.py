from typing import Optional

import pandas as pd
from lomas_handler import (
    InternalServerException,
    InvalidQueryException,
)

from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.utils.collection_models import Metadata


class PathConnector(DataConnector):
    """
    DataConnector for dataset located at constant path.

    Path can be local or remote (http).
    """

    def __init__(
        self,
        metadata: Metadata,
        dataset_path: str,
    ) -> None:
        """Initializer. Does not load the dataset in memory yet.

        Args:
            metadata (Metadata): The metadata dictionary.
            dataset_path (str): path of the dataset (local or remote).
        """
        super().__init__(metadata)
        self.ds_path: str = dataset_path
        self.df: Optional[pd.DataFrame] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Raises:
            InternalServerException: If the file format is not supported.

        Returns:
            pd.DataFrame: pandas dataframe of dataset
        """
        if self.df is None:
            if self.ds_path.endswith(".csv"):
                try:
                    self.df = pd.read_csv(
                        self.ds_path,
                        dtype=self.dtypes,
                        parse_dates=self.datetime_columns,
                    )
                except Exception as err:
                    raise InternalServerException(
                        "Error reading csv at http path:" f"{self.ds_path}: {err}",
                    ) from err
            else:
                return InvalidQueryException(
                    "File type other than .csv not supported for"
                    "loading into pandas DataFrame."
                )

        return self.df
