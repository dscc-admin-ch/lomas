from abc import ABC, abstractmethod
from fastapi import Header, HTTPException
from typing import Dict

from utils.constants import (
    SUPPORTED_LIBS,
    LIB_SMARTNOISE_SQL,
    DATASET_PATHS,
    DATASET_METADATA_PATHS,
)
from database.database import Database
from dp_queries.input_models import BasicModel
from dp_queries.utils import stream_dataframe
from utils.loggr import LOG


class DPQuerier(ABC):
    """
    Overall query to external DP library
    """

    @abstractmethod
    def __init__(self) -> None:
        """
        Initialise with specific dataset
        """
        pass

    @abstractmethod
    def cost(self, query_str: str, eps: float, delta: float) -> [float, float]:
        """
        Estimate cost of query
        """
        pass

    @abstractmethod
    def query(self, query_str: str, eps: float, delta: float) -> str:
        """
        Does the query and return the response
        """
        pass


class QuerierManager(ABC):
    """
    Manages the DPQueriers for the different datasets and libraries

    Holds a reference to the database in order to get information about
    the datasets.

    We make the _add_dataset function private to enforce lazy loading of
    queriers.
    """

    database: Database

    def __init__(self, database: Database) -> None:
        self.database = database

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

    def __init__(self, database: Database) -> None:
        super().__init__(database)
        self.dp_queriers = {}
        return

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

        # Initialize dict
        self.dp_queriers[dataset_name] = {}

        for lib in SUPPORTED_LIBS:
            if lib == LIB_SMARTNOISE_SQL:
                ds_path = DATASET_PATHS[dataset_name]
                ds_metadata_path = DATASET_METADATA_PATHS[dataset_name]
                from dp_queries.smartnoise_json.smartnoise_sql import (
                    SmartnoiseSQLQuerier,
                )

                querier = SmartnoiseSQLQuerier(ds_metadata_path, ds_path)

                self.dp_queriers[dataset_name][lib] = querier
            # elif ... :
            else:
                raise Exception(
                    f"Trying to create a querier for library {lib}. "
                    "This should never happen."
                )

    def get_querier(self, dataset_name: str, query_type: str) -> DPQuerier:
        if dataset_name not in self.dp_queriers:
            self._add_dataset(dataset_name)

        return self.dp_queriers[dataset_name][query_type]


class QueryHandler:
    """
    Query handler for the server.

    Holds a reference to the database and uses a BasicQuerierManager
    to manage the queriers. TODO make this configurable?
    """

    database: Database
    querier_manager: BasicQuerierManager

    def __init__(self, database: Database) -> None:
        self.database = database
        self.querier_manager = BasicQuerierManager(database)
        return

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
                f"Failed to get querier for dataset"
                f"{query_json.dataset_name}: {str(e)}"
            )
            raise HTTPException(
                404,
                f"Failed to get querier for dataset"
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
        eps_cost, delta_cost = dp_querier.cost(
            query_json.query_str, query_json.epsilon, query_json.delta
        )
        response = {"epsilon_cost": eps_cost, "delta_cost": delta_cost}
        return response

    def handle_query(
        self,
        query_type: str,
        query_json: BasicModel,
        user_name: str = Header(None),
    ):
        # Get querier
        dp_querier = self._get_querier(query_type, query_json)

        # Check that user may query
        if not self.database.may_user_query(user_name):
            LOG.warning(
                f"User {user_name} is trying to query before end of \
                previous query. Returning without response."
            )
            return {
                "requested_by": user_name,
                "state": "No response. Already a query running.",
            }

        # Block access to other queries to user
        self.database.set_may_user_query(user_name, False)

        # Get cost of the query
        eps_cost, delta_cost = dp_querier.cost(
            query_json.query_str, query_json.epsilon, query_json.delta
        )

        # Check that enough budget to to the query
        eps_max_user, delta_max_user = self.database.get_max_budget(
            user_name, query_json.dataset_name
        )

        eps_curr_user, delta_curr_user = self.database.get_current_budget(
            user_name, query_json.dataset_name
        )

        # If enough budget
        if ((eps_max_user - eps_curr_user) >= eps_cost) and (
            (delta_max_user - delta_curr_user) >= delta_cost
        ):
            # Query
            try:
                query_response = dp_querier.query(
                    query_json.query_str, query_json.epsilon, query_json.delta
                )
            except HTTPException as he:
                self.database.set_may_user_query(user_name, True)
                LOG.exception(he)
                raise he
            except Exception as e:
                self.database.set_may_user_query(user_name, True)
                LOG.exception(e)
                raise HTTPException(500, str(e))

            # Deduce budget from user
            self.database.update_budget(
                user_name, query_json.dataset_name, eps_cost, delta_cost
            )

            # Add query to db (for archive)
            self.database.save_query(
                user_name,
                query_json.dataset_name,
                eps_cost,
                delta_cost,
                query_json.query_str,
            )
            
            response = {
                "requested_by": user_name,
                "state": "Query successful.",
                "query_response": query_response.to_dict(orient="tight"),
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

        # Return budget metadata to user
        response["current_epsilon"] = eps_curr_user
        response["current_delta"] = delta_curr_user
        response["max_epsilon"] = eps_max_user
        response["max_delta"] = delta_max_user

        # Re-enable user to query
        self.database.set_may_user_query(user_name, True)

        # Return response
        return response
