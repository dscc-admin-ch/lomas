from typing import Literal

import pandas as pd

from lomas_server.data_connector.data_connector import DataConnector


class InMemoryConnector(DataConnector):
    """DataConnector for a dataset created from an in-memory pandas DataFrame."""

    type: Literal["InMemoryConnector"] = "InMemoryConnector"

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Returns:
            pd.DataFrame: pandas dataframe of dataset (a copy)
        """
        assert self.df is not None
        # We use a copy here for safety.
        return self.df.copy()  # pylint: disable=no-member
