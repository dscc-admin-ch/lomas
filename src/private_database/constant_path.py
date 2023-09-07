from private_database.private_database import PrivateDatabase

import pandas as pd


class ConstantPath(PrivateDatabase):
    """
    Class to fetch dataset from constant path
    """

    def __init__(self, dataset_path) -> None:
        """
        Parameters:
            - dataset_path: path of the dataset
        """
        self.ds_path = dataset_path

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        return pd.read_csv(self.ds_path)
