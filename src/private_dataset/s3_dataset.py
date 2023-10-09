from private_dataset.private_dataset import PrivateDataset

import boto3
import shutil
import os
import pandas as pd
import tempfile


class S3Dataset(PrivateDataset):
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
        obj = self.client.get_object(Bucket=self.s3_bucket, Key=self.s3_key)
        return pd.read_csv(obj["Body"])

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
            self.client.download_file(
                self.s3_bucket, self.s3_key, self.local_path
            )

        return self.local_path
