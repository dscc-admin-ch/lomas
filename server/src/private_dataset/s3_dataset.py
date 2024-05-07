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
        s3_parameters: dict,
    ) -> None:
        """_summary_

        Args:
            metadata (dict): _description_
            s3_parameters (dict): informations to access metadata
        """
        super().__init__(metadata)

        self.client = boto3.client(
            "s3",
            endpoint_url=s3_parameters["s3_endpoint"],
            aws_access_key_id=s3_parameters["s3_aws_access_key_id"],
            aws_secret_access_key=s3_parameters["aws_secret_access_key"],
        )
        self.s3_bucket: str = s3_parameters["s3_bucket"]
        self.s3_key: str = s3_parameters["s3_key"]
        self.df: Optional[pd.DataFrame] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Raises:
            InternalServerException: _description_

        Returns:
            pd.DataFrame: pandas dataframe of dataset
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
                ) from err

            # Notify observer since memory usage has changed
            for observer in self.dataset_observers:
                observer.update_memory_usage()

        return self.df
