import os
import tempfile
from typing import Optional
import boto3
import pandas as pd
from private_dataset.private_dataset import PrivateDataset
from utils.error_handler import InternalServerException


class S3Dataset(PrivateDataset):
    """
    Class to fetch dataset from constant path
    """

    def __init__(
        self,
        metadata: dict,
        s3_bucket: str,
        s3_key: str,
        endpoint_url: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
    ) -> None:
        """
        Parameters:
            - s3_bucket: s3 bucket of the dataset
            - s3_key: s3 key of the path to the dataset
        """
        super().__init__(metadata)

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        self.s3_bucket: str = s3_bucket
        self.s3_key: str = s3_key
        self.df: Optional[pd.DataFrame] = None
        self.local_path: Optional[str] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Returns:
            - pandas dataframe of dataset
        """
        if self.df is None:
            obj = self.client.get_object(
                Bucket=self.s3_bucket, Key=self.s3_key
            )
            try:
                self.df = pd.read_csv(obj["Body"], dtype=self.dtypes)
            except Exception as err:
                raise InternalServerException(
                    "Error reading csv at s3 path:"
                    + f"{self.s3_bucket}/{self.s3_key}: {err}"
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
            file_name = self.s3_key
            self.local_path = os.path.join(self.local_dir, file_name)

            # Download
            self.client.download_file(
                self.s3_bucket, self.s3_key, self.local_path
            )

        return self.local_path
