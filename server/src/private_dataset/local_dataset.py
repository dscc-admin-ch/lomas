import os
import shutil
import tempfile
from private_dataset.private_dataset import PrivateDataset

import pandas as pd


class LocalDataset(PrivateDataset):
    """
    Class to fetch dataset from constant path
    """

    def __init__(self, metadata, dataset_path) -> None:
        """
        Parameters:
            - dataset_path: path of the dataset
        """
        super().__init__(metadata)
        self.ds_path = dataset_path
        self.local_path = None
        self.local_dir = None

    def __del__(self):
        """
        Cleans up the temporary directory used for storing
        the dataset locally if needed.
        """
        if self.local_dir is not None:
            shutil.rmtree(self.local_dir)

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        # TODO add support for more file types (e.g. parquet, etc..).
        if self.ds_path.endswith(".csv"):
            return pd.read_csv(self.ds_path)
        else:
            # TODO make this cleaner
            return Exception(
                "File type other than .csv not supported for"
                "loading into pandas DataFrame."
            )

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
