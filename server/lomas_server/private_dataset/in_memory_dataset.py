import pandas as pd

from private_dataset.private_dataset import PrivateDataset
from utils.collection_models import Metadata


class InMemoryDataset(PrivateDataset):
    """
    PrivateDataset for a dataset created from an in-memory pandas DataFrame.
    """

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
        self.df = dataset_df.copy()

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Returns:
            pd.DataFrame: pandas dataframe of dataset (a copy)
        """
        # We use a copy here for safety.
        return self.df.copy()
