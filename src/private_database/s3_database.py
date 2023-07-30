from private_database.private_database import PrivateDatabase

import boto3
import pandas as pd


class S3Database(PrivateDatabase):
    """
    Class to fetch dataset from constant path
    """

    def __init__(self, s3_bucket: str, s3_prefix: str) -> None:
        """
        Parameters:
            - dataset_name: name of the dataset
        """
        self.ds_path = f"s3://{s3_bucket}/{s3_prefix}"

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        return boto3.read(self.ds_path)
