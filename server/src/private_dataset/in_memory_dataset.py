from typing import Dict, Union

import pandas as pd

from private_dataset.private_dataset import PrivateDataset


class InMemoryDataset(PrivateDataset):
    """
    Class to hold a dataset created from an in-memory pandas DataFrame
    """

    def __init__(
        self,
        metadata: Dict[str, Union[int, bool, Dict[str, Union[str, int]]]],
        dataset_df: pd.DataFrame,
    ) -> None:
        """
        Parameters:
            - dataset_df: Dataframe of the dataset
        """
        super().__init__(metadata)
        self.df = dataset_df.copy()

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset (a copy)
        """
        # We use a copy here for safety.
        return self.df.copy()
