from collections import OrderedDict

from admin_database.admin_database import AdminDatabase
from dataset_store.dataset_store import DatasetStore
from dataset_store.private_dataset_observer import PrivateDatasetObserver
from dp_queries.dp_libraries.utils import querier_factory
from dp_queries.dp_querier import DPQuerier
from private_dataset.utils import private_dataset_factory
from utils.loggr import LOG


class LRUDatasetStore(DatasetStore, PrivateDatasetObserver):
    """
    Implementation of the DatasetStore interface, with an LRU cache.

    Subscribes to the PrivateDatasets to get notified if their memory usage
    changes and then clears the cache accordingly in order stay below
    the maximum memory usage.
    """

    dataset_cache: OrderedDict = {}

    def __init__(
        self, admin_database: AdminDatabase, max_memory_usage: int = 1024
    ) -> None:
        super().__init__(admin_database)
        self.admin_database = admin_database
        self.max_memory_usage = max_memory_usage

        self.dataset_cache = OrderedDict()
        self.memory_usage = 0

    def _add_dataset(self, dataset_name: str) -> None:
        """
        Adds all queriers for a dataset.
        The source data is fetched from an online csv, the paths are stored
        as constants for now.
        """
        # Should not call this function if dataset already present.
        assert (
            dataset_name not in self.dataset_cache.keys()
        ), "BasicQuerierManager: \
        Trying to add a dataset already in self.dp_queriers"

        # Make private dataset
        private_dataset = private_dataset_factory(
            dataset_name, self.admin_database
        )
        private_dataset.subscribe_for_memory_usage_updates(self)

        # Remove least recently used dataset from cache if not enough space
        private_dataset_mem_usage = private_dataset.get_memory_usage()
        while (
            self.memory_usage + private_dataset_mem_usage
            > self.max_memory_usage
        ):
            evicted_ds_name, evicted_ds = self.dataset_cache.popitem(
                last=False
            )
            self.memory_usage -= evicted_ds.get_memory_usage()
            LOG.info(f"Dataset {evicted_ds_name} was evicted from cache.")

        self.dataset_cache[dataset_name] = private_dataset
        self.memory_usage += private_dataset_mem_usage

        LOG.info(f"New dataset cache size: {self.memory_usage} MiB")

        return

    def update_memory_usage(self) -> None:
        """
        Remove least recently used datasets until the cache
        is back to below its maximum size.
        """
        self.memory_usage = sum(
            [
                private_ds.get_memory_usage()
                for private_ds in self.dataset_cache.values()
            ]
        )

        while self.memory_usage > self.max_memory_usage:
            evicted_ds_name, evicted_ds = self.dataset_cache.popitem(
                last=False
            )
            self.memory_usage -= evicted_ds.get_memory_usage()
            LOG.info(f"Dataset {evicted_ds_name} was evicted from cache.")

        LOG.info(f"New dataset cache size: {self.memory_usage} MiB")

    def get_querier(self, dataset_name: str, library: str) -> DPQuerier:
        # Add dataset to cache if not present and get it.
        if dataset_name not in self.dataset_cache:
            self._add_dataset(dataset_name)
        else:
            self.dataset_cache.move_to_end(dataset_name)
        assert dataset_name in self.dataset_cache.keys()

        private_dataset = self.dataset_cache[dataset_name]
        return querier_factory(library, private_dataset)
