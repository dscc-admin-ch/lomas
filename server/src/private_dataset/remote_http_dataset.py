import os
import tempfile
import urllib
from private_dataset.private_dataset import PrivateDataset

import pandas as pd


class RemoteHTTPDataset(PrivateDataset):
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

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        if self.df is None:
            # TODO add support for more file types (e.g. parquet, etc..).
            if self.ds_path.endswith(".csv"):
                self.df = pd.read_csv(self.ds_path)
            else:
                # TODO make this cleaner
                return Exception(
                    "File type other than .csv not supported for"
                    "loading into pandas DataFrame."
                )

            # Notify observer since memory usage has changed
            [
                observer.update_memory_usage()
                for observer in self.dataset_observers
            ]

        return self.df

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

            # Download
            urllib.request.urlretrieve(self.ds_path, self.local_path)

        return self.local_path
