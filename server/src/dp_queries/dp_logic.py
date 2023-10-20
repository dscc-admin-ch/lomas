from fastapi import Header, HTTPException


from admin_database.admin_database import AdminDatabase
from utils.input_models import BasicModel
from dataset_store.basic_dataset_store import BasicDatasetStore
from dataset_store.lru_dataset_store import LRUDatasetStore
from constants import SUPPORTED_LIBS
from utils.loggr import LOG


class QueryHandler:
    """
    Query handler for the server.

    Holds a reference to the user database and uses a BasicQuerierManager
    to manage the queriers. TODO make this configurable?
    """

    admin_database: AdminDatabase
    querier_manager: BasicDatasetStore

    def __init__(self, admin_database: AdminDatabase) -> None:
        self.admin_database = admin_database
        self.querier_manager = LRUDatasetStore(admin_database, max_memory_usage=512)

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
