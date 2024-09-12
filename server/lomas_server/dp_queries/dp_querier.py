from abc import ABC, abstractmethod

from pydantic import BaseModel

from data_connector.data_connector import DataConnector


class DPQuerier(ABC):
    """
    Abstract Base Class for Queriers to external DP library.

    A querier type is specific to a DP library and
    a querier instance is specific to a DataConnector instance.
    """

    def __init__(self, data_connector: DataConnector) -> None:
        """Initialise with specific dataset

        Args:
            data_connector (DataConnector): The private dataset to query.
        """
        self.data_connector = data_connector

    @abstractmethod
    def cost(self, query_json: BaseModel) -> tuple[float, float]:
        """
        Estimate cost of query.

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Returns:
            tuple[float, float]: The tuple of costs, the first value is
                the epsilon cost, the second value is the delta value.
        """

    @abstractmethod
    def query(self, query_json: BaseModel) -> str:
        """
        Perform the query and return the response.

        Args:
            query_json (BaseModel): The JSON request object for the query.

        Returns:
            str: The JSON encoded string representation of the query result.
        """
