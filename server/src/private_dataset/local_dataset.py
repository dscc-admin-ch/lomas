import os
import shutil
import tempfile
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
        self.local_path: Optional[str] = None

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

    def get_local_path(self) -> str:
        """
        Get the path to a local copy of the source file
        Returns:
            - path
        """

        if self.local_path is None:
            # Create temp dir and file
            self.local_dir = tempfile.mkdtemp()
            file_name = self.ds_path.split("/")[-1]
            self.local_path = os.path.join(self.local_dir, file_name)

            # We make a local copy here for added safety:
            # => The original version stays untouched.
            shutil.copyfile(self.ds_path, self.local_path)

        return self.local_path
