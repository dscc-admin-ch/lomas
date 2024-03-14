from typing import Dict

from admin_database.admin_database import AdminDatabase
from constants import (
    SUPPORTED_LIBS,
    LIB_DIFFPRIVLIB,
    LIB_OPENDP,
    LIB_SMARTNOISE_SQL,
)
from dp_queries.dp_querier import DPQuerier
from dataset_store.dataset_store import DatasetStore
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

    dp_queriers: Dict[str, Dict[str, DPQuerier]] = None

    def __init__(self, admin_database: AdminDatabase) -> None:
        super().__init__(admin_database)
        self.dp_queriers = {}
        self.admin_database = admin_database

    def _add_dataset(self, dataset_name: str) -> None:
        """
        Adds all queriers for a dataset.
        The source data is fetched from an online csv, the paths are stored
        as constants for now.

        TODO Get the info from the metadata stored in the db.
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

        for lib in SUPPORTED_LIBS:
            if lib == LIB_SMARTNOISE_SQL:
                from dp_queries.dp_libraries.smartnoise_sql import (
                    SmartnoiseSQLQuerier,
                )

                querier = SmartnoiseSQLQuerier(private_dataset)
            elif lib == LIB_OPENDP:
                from dp_queries.dp_libraries.open_dp import OpenDPQuerier

                querier = OpenDPQuerier(private_dataset)
            elif lib == LIB_DIFFPRIVLIB: # TODO
                pass
            else:
                raise Exception(
                    f"Trying to create a querier for library {lib}. "
                    "This should never happen."
                )
            self.dp_queriers[dataset_name][lib] = querier

    def get_querier(self, dataset_name: str, query_type: str) -> DPQuerier:
        if dataset_name not in self.dp_queriers:
            self._add_dataset(dataset_name)

        return self.dp_queriers[dataset_name][query_type]
