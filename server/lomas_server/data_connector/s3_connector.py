from functools import cached_property
from typing import Literal

import boto3
import pandas as pd
from pydantic import computed_field

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import DSS3Access
from lomas_server.data_connector.data_connector import DataConnector


class S3Connector(DataConnector):
    """DataConnector for dataset in S3 storage."""

    type: Literal["S3Connector"] = "S3Connector"

    credentials: DSS3Access

    # private to avoid serialization
    @cached_property
    def _client(self) -> boto3.session.Session.client:
        return boto3.client(
            "s3",
            endpoint_url=str(self.credentials.endpoint_url),
            aws_access_key_id=self.credentials.access_key_id,
            aws_secret_access_key=self.credentials.secret_access_key,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bucket(self) -> str:
        return self.credentials.bucket

    @computed_field  # type: ignore[prop-decorator]
    @property
    def key(self) -> str:
        return self.credentials.key

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format.

        Raises:
            InternalServerException: If the dataset cannot be read.

        Returns:
            pd.DataFrame: pandas dataframe of dataset
        """
        if self.df is not None:
            return self.df

        obj = self._client.get_object(Bucket=self.bucket, Key=self.key)
        try:
            self.df = pd.read_csv(obj["Body"], dtype=self.dtypes, parse_dates=self.datetime_columns)
            return self.df
        except Exception as err:
            raise InternalServerException(
                "Error reading csv at s3 path:" + f"{self.bucket}/{self.key}: {err}"
            ) from err
