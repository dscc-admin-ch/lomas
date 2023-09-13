from private_database.private_database import PrivateDatabase

import boto3
import pandas as pd


class S3Database(PrivateDatabase):
    """
    Class to fetch dataset from constant path
    """

    def __init__(self, s3_bucket: str, s3_key: str) -> None:
        """
        Parameters:
            - s3_bucket: s3 bucket of the dataset
            - s3_key: s3 key of the path to the dataset
        """
        self.client = boto3.client("s3")
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        obj = self.client.get_object(Bucket=self.s3_bucket, Key=self.s3_key)
        return pd.read_csv(obj["Body"])
