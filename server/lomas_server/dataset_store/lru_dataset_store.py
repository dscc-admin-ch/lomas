from collections import OrderedDict
from typing import List

from admin_database.admin_database import AdminDatabase
from data_connector.data_connector import DataConnector
from data_connector.factory import data_connector_factory
from dataset_store.data_connector_observer import DataConnectorObserver
from dataset_store.dataset_store import DatasetStore
from dp_queries.dp_libraries.factory import querier_factory
from dp_queries.dp_querier import DPQuerier
from utils.config import PrivateDBCredentials
from utils.error_handler import InternalServerException
from utils.logger import LOG


class LRUDatasetStore(DatasetStore, DataConnectorObserver):
    """
    Implementation of the DatasetStore interface, with an LRU cache.

    Subscribes to the DataConnectors to get notified if their memory usage
    changes and then clears the cache accordingly in order stay below
    the maximum memory usage.
    """

    dataset_cache: OrderedDict[str, DataConnector]

    def __init__(
        self,
        admin_database: AdminDatabase,
        private_db_credentials: List[PrivateDBCredentials],
        max_memory_usage: int = 1024,
    ) -> None:
        """Initializer.

        Args:
            admin_database (AdminDatabase): An initialized AdminDatabase.
            max_memory_usage (int, optional): Maximum memory usage limit\
                for the manager.. Defaults to 1024.
            private_db_credentials (List[PrivateDBCredentials]):\
                The private database credentials from the server config.
        """
        super().__init__(admin_database, private_db_credentials)
        self.max_memory_usage = max_memory_usage

        self.dataset_cache = OrderedDict()
        self.memory_usage = 0

    def _add_dataset(self, dataset_name: str) -> None:
        """Adds a dataset to the manager.

        Makes sure the memory usage limit is not exceeded.

        Args:
            dataset_name (str): The name of the dataset.
        """
        # Should not call this function if dataset already present.
        assert (
            dataset_name not in self.dataset_cache.keys()
        ), "BasicQuerierManager: \
        Trying to add a dataset already in self.dp_queriers"

        # Make private dataset
        data_connector = data_connector_factory(
            dataset_name, self.admin_database, self.private_db_credentials
        )
        data_connector.subscribe_for_memory_usage_updates(self)

        # Remove least recently used dataset from cache if not enough space
        data_connector_mem_usage = data_connector.get_memory_usage()

        if data_connector_mem_usage > self.max_memory_usage:
            raise InternalServerException(
                f"Dataset {dataset_name} too large"
                "to fit in dataset manager memory."
            )

        self.dataset_cache[dataset_name] = data_connector
        self.memory_usage += data_connector_mem_usage

        LOG.info(f"New dataset cache size: {self.memory_usage} MiB")
        self.update_memory_usage()

    def update_memory_usage(self) -> None:
        """Remove least recently used datasets until the cache
        is back to below or equal to its maximum size.
        """
        self.memory_usage = sum(
            private_ds.get_memory_usage()
            for private_ds in self.dataset_cache.values()
        )

        while self.memory_usage > self.max_memory_usage:
            evicted_ds_name, evicted_ds = self.dataset_cache.popitem(
                last=False
            )
            self.memory_usage -= evicted_ds.get_memory_usage()
            LOG.info(f"Dataset {evicted_ds_name} was evicted from cache.")

        LOG.info(f"New dataset cache size: {self.memory_usage} MiB")

    def get_querier(self, dataset_name: str, library: str) -> DPQuerier:
        """Returns the querier for the given dataset and library

        Args:
            dataset_name (str): The dataset name.
            library (str): The type of DP library.
                One of :py:class:`constants.DPLibraries`

        Returns:
            DPQuerier: The DPQuerier for the specified dataset and library.
        """
        # Add dataset to cache if not present and get it.
        if dataset_name not in self.dataset_cache:
            self._add_dataset(dataset_name)
        else:
            self.dataset_cache.move_to_end(dataset_name)
        assert dataset_name in self.dataset_cache.keys()

        data_connector = self.dataset_cache[dataset_name]
        return querier_factory(library, data_connector)
