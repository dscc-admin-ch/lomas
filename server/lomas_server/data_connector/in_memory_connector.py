import pandas as pd
from lomas_core.models.collections import Metadata

from lomas_server.data_connector.data_connector import DataConnector


class InMemoryConnector(DataConnector):
    """DataConnector for a dataset created from an in-memory pandas DataFrame."""

    def __init__(
        self,
        metadata: Metadata,
        dataset_df: pd.DataFrame,
    ) -> None:
        """Initializer.

        Args:
            metadata (Metadata): Metadata dictionary.
            dataset_df (pd.DataFrame): Dataframe of the dataset
        """
        super().__init__(metadata)
        self.df: pd.DataFrame = dataset_df.copy()

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Returns:
            pd.DataFrame: pandas dataframe of dataset (a copy)
        """
        # We use a copy here for safety.
        return self.df.copy()
