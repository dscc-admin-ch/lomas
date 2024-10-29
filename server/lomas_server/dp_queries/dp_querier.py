from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    InternalServerException,
    InvalidQueryException,
    UnauthorizedAccessException,
)
from lomas_core.models.requests import (  # pylint: disable=W0611
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import (  # pylint: disable=W0611
    QueryResponse,
    QueryResultTypeAlias,
)

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.data_connector.data_connector import DataConnector

RequestModelGeneric = TypeVar("RequestModelGeneric", bound="LomasRequestModel")
QueryModelGeneric = TypeVar("QueryModelGeneric", bound="QueryModel")
QueryResultGeneric = TypeVar("QueryResultGeneric", bound="QueryResultTypeAlias")


class DPQuerier(
    ABC, Generic[RequestModelGeneric, QueryModelGeneric, QueryResultGeneric]
):
    """
    Abstract Base Class for Queriers to external DP library.

    A querier type is specific to a DP library and
    a querier instance is specific to a DataConnector instance.
    """

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: AdminDatabase,
    ) -> None:
        """Initialise with specific dataset.

        Args:
            data_connector (DataConnector): The private dataset to query.
            admin_database (AdminDatabase): An initialized instance of
                an AdminDatabase.
        """
        self.data_connector = data_connector
        self.admin_database = admin_database

    @abstractmethod
    def cost(self, query_json: RequestModelGeneric) -> tuple[float, float]:
        """
        Estimate cost of query.

        Args:
            query_json (RequestModelGeneric): The input object of the request.
                Must be a subclass of LomasRequestModel.
        Returns:
            tuple[float, float]: The tuple of costs, the first value is
                the epsilon cost, the second value is the delta value.
        """

    @abstractmethod
    def query(self, query_json: QueryModelGeneric) -> QueryResultGeneric:
        """
        Perform the query and return the response.

        Args:
            query_json (QueryModelGeneric): The input object of the query.
              Must be a subclass of QueryModel.

        Returns:
            dict | int | float | List[Any] | Any | str:
                The query result, to be added to the response dict.
        """

    def handle_query(
        self,
        query_json: QueryModel,
        user_name: str,
    ) -> QueryResponse:
        """
        Handle DP query.

        Args:
            query_json (LomasRequestModel): The input object of the query.
              Must be a subclass of QueryModel.
            user_name (str, optional): User name.

        Raises:
            UnauthorizedAccessException: A query is already
                ongoing for this user,
            the user does not exist or does not have access to the dataset.
            InvalidQueryException: If the query is not valid.
            InternalServerException: For any other unforseen exceptions.

        Returns:
            QueryResponse: The response object. # TODO remove what is next.

            A dictionary containing:
                - requested_by (str): The user name.
                - query_response (pd.DataFrame): A DataFrame containing
                  the query response.
                - spent_epsilon (float): The amount of epsilon budget spent
                for the query.
                - spent_delta (float): The amount of delta budget spent
                  for the query.
        """
        # Block access to other queries to user
        if not self.admin_database.get_and_set_may_user_query(user_name, False):
            raise UnauthorizedAccessException(
                f"User {user_name} is trying to query"
                + " before end of previous query."
            )

        try:
            # Get cost of the query
            eps_cost, delta_cost = self.cost(query_json)  # type: ignore [arg-type]

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
                query_result = self.query(query_json)  # type: ignore [arg-type]
            except KNOWN_EXCEPTIONS as e:
                raise e
            except Exception as e:
                raise InternalServerException(str(e)) from e

            # Deduce budget from user
            self.admin_database.update_budget(
                user_name, query_json.dataset_name, eps_cost, delta_cost
            )

            response = QueryResponse(
                requested_by=user_name,
                result=query_result,
                epsilon=eps_cost,
                delta=delta_cost,
            )

            # Add query to db (for archive)
            self.admin_database.save_query(
                user_name, query_json, response
            )  # TODO 359 here

        except Exception as e:
            self.admin_database.set_may_user_query(user_name, True)
            raise e

        # Re-enable user to query
        self.admin_database.set_may_user_query(user_name, True)

        # Return response
        return response
