from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import FilePath, HttpUrl

from lomas_core.exceptions import InternalServerException, InvalidQueryException
from lomas_server.data_connector.data_connector import DataConnector


class PathConnector(DataConnector):
    """
    DataConnector for dataset located at constant path.

    Path can be local or remote (http).
    """

    type: Literal["PathConnector"] = "PathConnector"

    dataset_path: FilePath | HttpUrl

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Raises:
            InternalServerException: If the file format is not supported.

        Returns:
            pd.DataFrame: pandas dataframe of dataset
        """
        supported_filetypes = [".csv"]

        if self.df is not None:
            return self.df

        match self.dataset_path:
            case Path():
                path = self.dataset_path
            case HttpUrl():
                path = Path(self.dataset_path.path)

        if path.suffix not in supported_filetypes:
            raise InvalidQueryException(
                f"File type other than {supported_filetypes} not supported for loading into pandas DataFrame."
            )
        try:
            self.df = pd.read_csv(
                str(self.dataset_path),
                dtype=self.dtypes,
                parse_dates=self.datetime_columns,
            )
            return self.df
        except Exception as err:
            raise InternalServerException(
                f"Error reading csv at http path:{self.dataset_path}: {err}",
            ) from err
