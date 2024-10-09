from typing import Optional

import boto3
import pandas as pd
from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import DSS3Access, Metadata

from lomas_server.data_connector.data_connector import DataConnector


class S3Connector(DataConnector):
    """DataConnector for dataset in S3 storage."""

    def __init__(
        self,
        metadata: Metadata,
        credentials: DSS3Access,
    ) -> None:
        """Initializer.

        Args:
            metadata (Metadata): The metadata dictionary.
            s3_parameters (dict): informations to access metadata
        """
        super().__init__(metadata)

        self.client = boto3.client(
            "s3",
            endpoint_url=credentials.endpoint_url,
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
        )
        self.bucket: str = credentials.bucket
        self.key: str = credentials.key
        self.df: Optional[pd.DataFrame] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Raises:
            InternalServerException: If the dataset cannot be read.

        Returns:
            pd.DataFrame: pandas dataframe of dataset
        """
        if self.df is None:
            obj = self.client.get_object(Bucket=self.bucket, Key=self.key)
            try:
                self.df = pd.read_csv(obj["Body"], dtype=self.dtypes)
            except Exception as err:
                raise InternalServerException(
                    "Error reading csv at s3 path:" + f"{self.bucket}/{self.key}: {err}"
                ) from err

        return self.df
