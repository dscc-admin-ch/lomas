from typing import Dict

from admin_database.admin_database import AdminDatabase
from constants import DPLibraries
from dataset_store.dataset_store import DatasetStore
from dp_queries.dp_libraries.utils import querier_factory
from dp_queries.dp_querier import DPQuerier
from private_dataset.utils import private_dataset_factory


class BasicDatasetStore(DatasetStore):
    """
    Basic implementation of the QuerierManager interface.

    The queriers are initialized lazily and put into a dict.
    There is no memory management => The manager will fail if the datasets are
    too large to fit in memory.

    The _add_dataset method just gets the source data from csv files
    (links stored in constants).
    """

    dp_queriers: Dict[str, Dict[str, DPQuerier]] = {}

    def __init__(self, admin_database: AdminDatabase) -> None:
        super().__init__(admin_database)
        self.dp_queriers = {}
        self.admin_database = admin_database

    def _add_dataset(self, dataset_name: str) -> None:
        """
        Adds all queriers for a dataset.
        The source data is fetched from an online csv, the paths are stored
        as constants for now.
        """
        # Should not call this function if dataset already present.
        assert (
            dataset_name not in self.dp_queriers
        ), "BasicQuerierManager: \
        Trying to add a dataset already in self.dp_queriers"

        # Metadata and data getter
        private_dataset = private_dataset_factory(
            dataset_name, self.admin_database
        )

        # Initialize dict
        self.dp_queriers[dataset_name] = {}

        for lib in DPLibraries:
            querier = querier_factory(lib.value, private_dataset)
            self.dp_queriers[dataset_name][lib.value] = querier

    def get_querier(self, dataset_name: str, query_type: str) -> DPQuerier:
        if dataset_name not in self.dp_queriers:
            self._add_dataset(dataset_name)

        return self.dp_queriers[dataset_name][query_type]
