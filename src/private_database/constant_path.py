from utils.constants import DATASET_PATHS
from private_database.private_database import PrivateDatabase

import pandas as pd

class ConstantPath(PrivateDatabase):
    """
    Overall database management while server is running
    """

    def __init__(self, dataset_name) -> None:
        """
        Connects to the DB
        Parameters:
            - dataset_name: name of the dataset
        """
        self.ds_path = DATASET_PATHS[dataset_name]

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        return pd.read_csv(self.ds_path)
