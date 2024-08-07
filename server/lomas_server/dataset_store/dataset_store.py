from abc import ABC, abstractmethod

from admin_database.admin_database import AdminDatabase
from dp_queries.dp_querier import DPQuerier


class DatasetStore(ABC):
    """
    Manages the DPQueriers for the different datasets and libraries

    Holds a reference to the user database in order to get information
    about users.

    We make the _add_dataset function private to enforce lazy loading
    of queriers.
    """

    admin_database: AdminDatabase

    def __init__(self, admin_database: AdminDatabase) -> None:
        self.admin_database = admin_database

    @abstractmethod
    def _add_dataset(self, dataset_name: str) -> None:
        """Adds a dataset to the manager

        Args:
            dataset_name (str): The dataset name.
        """

    @abstractmethod
    def get_querier(self, dataset_name: str, library: str) -> DPQuerier:
        """Returns the querier for the given dataset and library

        Args:
            dataset_name (str): The dataset name.
            library (str): The type of DP library.
                One of :py:class:`constants.DPLibraries`

        Returns:
            DPQuerier: The DPQuerier for the specified dataset and library.
        """
