from abc import ABC, abstractmethod
import pandas as pd
import shutil

from constants import SSQL_METADATA_OPTIONS


class PrivateDataset(ABC):
    """
    Overall access to sensitive data
    """

    df = None
    local_path = None
    local_dir = None

    def __init__(self, metadata) -> None:
        """
        Connects to the DB
        Parameters:
            - metadata: The metadata for this dataset
        """
        self.metadata = metadata
        self.dtypes = get_dtypes(metadata)

    def __del__(self):
        """
        Cleans up the temporary directory used for storing
        the dataset locally if needed.
        """
        if self.local_dir is not None:
            shutil.rmtree(self.local_dir)

    @abstractmethod
    def get_local_path(self) -> str:
        """
        Get the path to  a local copy of the file.
        Returns:
            - path
        """
        pass

    @abstractmethod
    def get_pandas_df(self, dataset_name: str) -> pd.DataFrame:
        """
        Get the data in pandas dataframe format
        Parameters:
            - dataset_name: name of the private dataset
        """
        pass

    def get_metadata(self) -> dict:
        """
        Get the metadata for this dataset
        """
        return self.metadata


def get_dtypes(metadata: str):
    dtypes = {}
    for col_name, data in metadata[""]["Schema"]["Table"].items():
        if col_name in SSQL_METADATA_OPTIONS:
            continue
        dtypes[col_name] = data["type"]
    return dtypes
