from typing import Dict, Optional, Union

import pandas as pd

from private_dataset.private_dataset import PrivateDataset
from utils.error_handler import InternalServerException, InvalidQueryException


class LocalDataset(PrivateDataset):
    """
    Class to fetch dataset from constant path
    """

    def __init__(
        self,
        metadata: Dict[str, Union[int, bool, Dict[str, Union[str, int]]]],
        dataset_path: str,
    ) -> None:
        """
        Parameters:
            - dataset_path: path of the dataset
        """
        super().__init__(metadata)
        self.ds_path = dataset_path
        self.df: Optional[pd.DataFrame] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        if self.df is None:
            if self.ds_path.endswith(".csv"):
                try:
                    self.df = pd.read_csv(self.ds_path, dtype=self.dtypes)
                except Exception as err:
                    raise InternalServerException(
                        "Error reading local at http path:"
                        f"{self.ds_path}: {err}",
                    )
            else:
                return InvalidQueryException(
                    "File type other than .csv not supported for"
                    "loading into pandas DataFrame."
                )

            # Notify observer since memory usage has changed
            [
                observer.update_memory_usage()
                for observer in self.dataset_observers
            ]
        return self.df.copy(deep=True)
