from typing import Dict, List

from admin_database.admin_database import AdminDatabase
from constants import DPLibraries
from data_connector.factory import data_connector_factory
from dataset_store.dataset_store import DatasetStore
from dp_queries.dp_libraries.factory import querier_factory
from dp_queries.dp_querier import DPQuerier
from utils.config import PrivateDBCredentials


class BasicDatasetStore(DatasetStore):
    """
    Basic implementation of the QuerierManager interface.

    The queriers are initialized lazily and put into a dict.
    There is no memory management => The manager will fail if the datasets are
    too large to fit in memory.
    """

    dp_queriers: Dict[str, Dict[str, DPQuerier]] = {}

    def __init__(
        self,
        admin_database: AdminDatabase,
        private_db_credentials: List[PrivateDBCredentials],
    ) -> None:
        """Initializer.

        Args:
            admin_database (AdminDatabase): An initialized AdminDatabase.
            private_db_credentials (List[PrivateDBCredentials]):\
                The private database credentials from the server config.
        """
        super().__init__(admin_database, private_db_credentials)
        self.dp_queriers = {}

    def _add_dataset(self, dataset_name: str) -> None:
        """Adds a dataset to the manager.

        Args:
            dataset_name (str): The name of the dataset.
        """
        # Should not call this function if dataset already present.
        assert (
            dataset_name not in self.dp_queriers
        ), "BasicQuerierManager: \
        Trying to add a dataset already in self.dp_queriers"

        # Metadata and data getter
        data_connector = data_connector_factory(
            dataset_name, self.admin_database, self.private_db_credentials
        )

        # Initialize dict
        self.dp_queriers[dataset_name] = {}

        for lib in DPLibraries:
            querier = querier_factory(lib.value, data_connector)
            self.dp_queriers[dataset_name][lib.value] = querier

    def get_querier(self, dataset_name: str, query_type: str) -> DPQuerier:
        """
        Returns the querier for the given dataset and library

        Args:
            dataset_name (str): The dataset name.
            query_type (str): The type of DP library.
                One of :py:class:`constants.DPLibraries`

        Returns:
            DPQuerier: The DPQuerier for the specified dataset and library.
        """
        if dataset_name not in self.dp_queriers:
            self._add_dataset(dataset_name)

        return self.dp_queriers[dataset_name][query_type]
