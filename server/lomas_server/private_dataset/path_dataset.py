from typing import Dict, Optional, Union

import pandas as pd

from private_dataset.private_dataset import PrivateDataset
from utils.error_handler import InternalServerException, InvalidQueryException


class PathDataset(PrivateDataset):
    """
    PrivateDataset for dataset located at constant path.

    Path can be local or remote (http).
    """

    def __init__(
        self,
        metadata: Dict[str, Union[int, bool, Dict[str, Union[str, int]]]],
        dataset_path: str,
    ) -> None:
        """Initializer. Does not load the dataset in memory yet.

        Args:
            metadata (Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]):
                The metadata dictionary.
            dataset_path (str): path of the dataset (local or remote).
        """
        super().__init__(metadata)
        self.ds_path: str = dataset_path
        self.df: Optional[pd.DataFrame] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Raises:
            InternalServerException: If the file format is not supported.

        Returns:
            pd.DataFrame: pandas dataframe of dataset
        """
        if self.df is None:
            if self.ds_path.endswith(".csv"):
                try:
                    self.df = pd.read_csv(self.ds_path, dtype=self.dtypes)
                except Exception as err:
                    raise InternalServerException(
                        "Error reading csv at http path:"
                        f"{self.ds_path}: {err}",
                    ) from err
            else:
                return InvalidQueryException(
                    "File type other than .csv not supported for"
                    "loading into pandas DataFrame."
                )

            # Notify observer since memory usage has changed
            for observer in self.dataset_observers:
                observer.update_memory_usage()

        return self.df
