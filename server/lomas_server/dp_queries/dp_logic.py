from pydantic import BaseModel

from admin_database.admin_database import AdminDatabase
from constants import DPLibraries
from dataset_store.dataset_store import DatasetStore
from dp_queries.dp_querier import DPQuerier
from utils.error_handler import (
    CUSTOM_EXCEPTIONS,
    InternalServerException,
    InvalidQueryException,
    UnauthorizedAccessException,
)


class QueryHandler:
    """
    Query handler for the server.

    Holds a reference to the admin database and the DatasetStore.
    """

    admin_database: AdminDatabase
    dataset_store: DatasetStore

    def __init__(
        self, admin_database: AdminDatabase, dataset_store: DatasetStore
    ) -> None:
        """Initializer.

        Args:
            admin_database (AdminDatabase): An initialized instance of
                an AdminDatabase.
            dataset_store (DatasetStore): A dataset store.
        """
        self.admin_database = admin_database
        self.dataset_store = dataset_store

    def _get_querier(
        self,
        query_type: str,
        query_json: BaseModel,
    ) -> DPQuerier:
        """Internal function to get a correct querier.

        Get the querier for the query_type and dataset_name in
        the query_json.

        Args:
            query_type (str): The type of DP library, one of
            :py:class:DPLibraries`
            query_json (BasicModel): The JSON request object for the query.

        Raises:
            InternalServerException: If the query type does not exist.
            InternalServerException: If the querier cannot be received from
                the querier manager.

        Returns:
            DPQuerier: The correct querier instance for the given
                request and libray.
        """
        # Check query type
        supported_lib = [lib.value for lib in DPLibraries]
        if query_type not in supported_lib:
            raise InternalServerException(
                f"Query type {query_type} not supported in QueryHandler"
            )

        # Get querier
        try:
            dp_querier = self.dataset_store.get_querier(
                query_json.dataset_name, query_type
            )
        except InvalidQueryException as e:
            raise e
        except Exception as e:
            raise InternalServerException(
                "Failed to get querier for dataset "
                + f"{query_json.dataset_name}: {str(e)}"
            ) from e
        return dp_querier

    def estimate_cost(
        self,
        query_type: str,
        query_json: BaseModel,
    ) -> dict[str, float]:
        """Estimate query cost.

        Args:
            query_type (str): The type of DP library,
                one of :py:class:DPLibraries`
            query_json (BasicModel): The JSON request object for the query.

        Returns:
            dict[str, float]: Dictionary containing:
                - epsilon_cost (float): The estimated epsilon cost.
                - delta_cost (float): The estimated delta cost.
        """
        # Get querier
        dp_querier = self._get_querier(query_type, query_json)

        # Get cost of the query
        eps_cost, delta_cost = dp_querier.cost(query_json)

        return {"epsilon_cost": eps_cost, "delta_cost": delta_cost}

    def handle_query(
        self,
        query_type: str,
        query_json: BaseModel,
        user_name: str,
    ) -> dict:
        """
        Handle DP query.

        Args:
            query_type (str): The type of DP library,
                one of :py:class:DPLibraries`
            query_json (BasicModel): The JSON request object for the query.
            user_name (str, optional): User name.

        Raises:
            UnauthorizedAccessException: A query is already
                ongoing for this user,
            the user does not exist or does not have access to the dataset.
            InvalidQueryException: If the query is not valid.
            InternalServerException: For any other unforseen exceptions.

        Returns:
            dict: A dictionary containing:
                - requested_by (str): The user name.
                - query_response (pd.DataFrame): A DataFrame containing
                  the query response.
                - spent_epsilon (float): The amount of epsilon budget spent
                for the query.
                - spent_delta (float): The amount of delta budget spent
                  for the query.

        """
        # Check that user may query
        if not self.admin_database.may_user_query(user_name):
            raise UnauthorizedAccessException(
                f"User {user_name} is trying to query"
                + " before end of previous query."
            )

        # Block access to other queries to user
        self.admin_database.set_may_user_query(user_name, False)

        try:
            # Get querier
            dp_querier = self._get_querier(query_type, query_json)

            # Get cost of the query
            eps_cost, delta_cost = dp_querier.cost(query_json)

            # Check that enough budget to do the query
            try:
                (
                    eps_remain,
                    delta_remain,
                ) = self.admin_database.get_remaining_budget(
                    user_name, query_json.dataset_name
                )
            except UnauthorizedAccessException as e:
                raise e

            if (eps_remain < eps_cost) or (delta_remain < delta_cost):
                raise InvalidQueryException(
                    "Not enough budget for this query epsilon remaining "
                    f"{eps_remain}, delta remaining {delta_remain}."
                )

            # Query
            try:
                query_response = dp_querier.query(query_json)
            except CUSTOM_EXCEPTIONS as e:
                raise e
            except Exception as e:
                raise InternalServerException(e) from e

            # Deduce budget from user
            self.admin_database.update_budget(
                user_name, query_json.dataset_name, eps_cost, delta_cost
            )
            response = {
                "requested_by": user_name,
                "query_response": query_response,
                "spent_epsilon": eps_cost,
                "spent_delta": delta_cost,
            }

            # Add query to db (for archive)
            self.admin_database.save_query(user_name, query_json, response)

        except Exception as e:
            self.admin_database.set_may_user_query(user_name, True)
            raise e

        # Re-enable user to query
        self.admin_database.set_may_user_query(user_name, True)

        # Return response
        return response
