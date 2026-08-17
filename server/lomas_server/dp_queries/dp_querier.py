from abc import ABC, abstractmethod
from typing import TypeVar

from aio_pika.patterns.rpc import Proxy

from lomas_core.exceptions import (
    InvalidQueryException,
)
from lomas_core.models.requests import (
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import (
    Budget,
    QueryResponse,
    QueryResultT,
)
from lomas_server.data_connector.data_connector import DataConnector

RequestModelGeneric = TypeVar("RequestModelGeneric", bound=LomasRequestModel)
QueryModelGeneric = TypeVar("QueryModelGeneric", bound=QueryModel)
QueryResultGeneric = TypeVar("QueryResultGeneric", bound=QueryResultT)


class DPQuerier[
    RequestModelGeneric: LomasRequestModel,
    QueryModelGeneric: QueryModel,
    QueryResultGeneric: QueryResultT,
](ABC):
    """
    Abstract Base Class for Queriers to external DP library.

    A querier type is specific to a DP library and
    a querier instance is specific to a DataConnector instance.
    """

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: Proxy,
    ) -> None:
        """Initialise with specific dataset.

        Args:
            data_connector (DataConnector): The private dataset to query.
            admin_database (Proxy): A Proxy for an initialized instance of an AdminDatabase.
        """
        self.data_connector = data_connector
        self.admin_database = admin_database

    @abstractmethod
    def cost(self, query_json: RequestModelGeneric) -> Budget:
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
            query_json (QueryModelGeneric): The input object of the query.\
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
            query_json (QueryModel): The input object of the query.
            user_name (str, optional): User name.

        Raises:
            UnauthorizedAccessException: A query is already ongoing for this user,\
                the user does not exist or does not have access to the dataset.
            InvalidQueryException: If the query is not valid.
            InternalServerException: For any other unforseen exceptions.

        Returns:
            QueryResponse: The response object. # TODO remove what is next.
                - requested_by (str): The user name.
                - query_response (pd.DataFrame): A DataFrame containing the query response.
                - spent_epsilon (float): The amount of epsilon budget spent for the query.
                - spent_delta (float): The amount of delta budget spent for the query.
        """
        # Get cost of the query
        query_cost = self.cost(query_json)

        # Check that enough budget to do the query
        # Note: This is only to create an early failure if budget is not enough to start with.
        #       Budget check and update is done at the server in a single transaction once job is returned.
        rem_budget = self.admin_database.get_remaining_budget(
            user_name=user_name, dataset_name=query_json.dataset_name
        )

        if not (query_cost <= rem_budget):
            raise InvalidQueryException(f"Not enough budget for this query epsilon remaining {rem_budget}")

        # Query
        query_result = self.query(query_json)

        # Return query response
        return QueryResponse(
            requested_by=user_name,
            result=query_result,
            epsilon=query_cost.epsilon,
            delta=query_cost.delta,
        )
