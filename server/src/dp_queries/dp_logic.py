from abc import ABC, abstractmethod
from fastapi import Header, HTTPException
from typing import Dict, List

from utils.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    SUPPORTED_LIBS,
    LIB_OPENDP,
    LIB_SMARTNOISE_SQL,
)
from admin_database.admin_database import AdminDatabase
from dp_queries.input_models import BasicModel
from private_dataset.private_dataset import PrivateDataset
from private_dataset.utils import private_dataset_factory
from utils.dummy_dataset import make_dummy_dataset
from utils.loggr import LOG


class DPQuerier(ABC):
    """
    Overall query to external DP library
    """

    def __init__(
        self,
        metadata: dict,
        private_dataset: PrivateDataset = None,
        dummy: bool = False,
        dummy_nb_rows: int = DUMMY_NB_ROWS,
        dummy_seed: int = DUMMY_SEED,
    ) -> None:
        """
        Initialise with specific dataset
        """
        self.metadata = metadata

        if dummy:
            self.df = make_dummy_dataset(
                self.metadata, dummy_nb_rows, dummy_seed
            )
        else:
            self.df = private_dataset.get_pandas_df()

    @abstractmethod
    def cost(self, query_json: dict) -> List[float]:
        """
        Estimate cost of query
        """
        pass

    @abstractmethod
    def query(self, query_json: dict) -> str:
        """
        Does the query and return the response
        """
        pass


class QuerierManager(ABC):
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
        """
        Adds a dataset to the manager
        """
        pass

    @abstractmethod
    def get_querier(self, dataset_name: str, library: str) -> DPQuerier:
        """
        Returns the querier for the given dataset and library
        """
        pass


class BasicQuerierManager(QuerierManager):
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
        metadata = self.admin_database.get_dataset_metadata(dataset_name)
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

                querier = SmartnoiseSQLQuerier(metadata, private_dataset)
            elif lib == LIB_OPENDP:
                from dp_queries.dp_libraries.open_dp import OpenDPQuerier

                querier = OpenDPQuerier(metadata, private_dataset)
            # elif lib == LIB_DIFFPRIVLIB: TODO
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


class QueryHandler:
    """
    Query handler for the server.

    Holds a reference to the user database and uses a BasicQuerierManager
    to manage the queriers. TODO make this configurable?
    """

    admin_database: AdminDatabase
    querier_manager: BasicQuerierManager

    def __init__(self, admin_database: AdminDatabase) -> None:
        self.admin_database = admin_database
        self.querier_manager = BasicQuerierManager(admin_database)

    def _get_querier(
        self,
        query_type: str,
        query_json: BasicModel,
    ):
        # Check query type
        if query_type not in SUPPORTED_LIBS:
            e = f"Query type {query_type} not supported in QueryHandler"
            LOG.exception(e)
            raise HTTPException(404, str(e))

        # Get querier
        try:
            dp_querier = self.querier_manager.get_querier(
                query_json.dataset_name, query_type
            )
        except Exception as e:
            LOG.exception(
                f"Failed to get querier for dataset "
                f"{query_json.dataset_name}: {str(e)}"
            )
            raise HTTPException(
                404,
                f"Failed to get querier for dataset "
                f"{query_json.dataset_name}",
            )
        return dp_querier

    def estimate_cost(
        self,
        query_type: str,
        query_json: BasicModel,
    ):
        # Get querier
        dp_querier = self._get_querier(query_type, query_json)

        # Get cost of the query
        eps_cost, delta_cost = dp_querier.cost(query_json)

        return {"epsilon_cost": eps_cost, "delta_cost": delta_cost}

    def handle_query(
        self,
        query_type: str,
        query_json: BasicModel,
        user_name: str = Header(None),
    ):
        # Get querier
        dp_querier = self._get_querier(query_type, query_json)

        # Check that user may query
        if not self.admin_database.may_user_query(user_name):
            LOG.warning(
                f"User {user_name} is trying to query before end of \
                previous query. Returning without response."
            )
            return {
                "requested_by": user_name,
                "state": "No response. Already a query running.",
            }

        # Block access to other queries to user
        self.admin_database.set_may_user_query(user_name, False)

        # Get cost of the query
        eps_cost, delta_cost = dp_querier.cost(query_json)

        # Check that enough budget to do the query
        (
            eps_remaining,
            delta_remaining,
        ) = self.admin_database.get_remaining_budget(
            user_name, query_json.dataset_name
        )

        # If enough budget
        if (eps_remaining >= eps_cost) and (delta_remaining >= delta_cost):
            # Query
            try:
                query_response = dp_querier.query(query_json)
            except HTTPException as he:
                self.admin_database.set_may_user_query(user_name, True)
                LOG.exception(he)
                raise he
            except Exception as e:
                self.admin_database.set_may_user_query(user_name, True)
                LOG.exception(e)
                raise HTTPException(500, str(e))

            # Deduce budget from user
            self.admin_database.update_budget(
                user_name, query_json.dataset_name, eps_cost, delta_cost
            )

            # Add query to db (for archive)
            self.admin_database.save_query(
                user_name,
                query_json.dataset_name,
                eps_cost,
                delta_cost,
                query_json,
            )

            LOG.warning(f"response {query_response}")
            response = {
                "requested_by": user_name,
                "state": "Query successful.",
                "query_response": query_response,
                "spent_epsilon": eps_cost,
                "spent_delta": delta_cost,
            }

        # If not enough budget, do not query and do not update budget.
        else:
            response = {
                "requested_by": user_name,
                "state": "Not enough budget to query. Nothing was done.",
                "spent_epsilon": 0,
                "spent_delta": 0,
            }

        # Check that enough budget to do the query
        (
            eps_remaining,
            delta_remaining,
        ) = self.admin_database.get_remaining_budget(
            user_name, query_json.dataset_name
        )
        # Return budget metadata to user
        response["remaining_epsilon"] = eps_remaining
        response["remaining_delta"] = delta_remaining

        # Re-enable user to query
        self.admin_database.set_may_user_query(user_name, True)

        # Return response
        return response
