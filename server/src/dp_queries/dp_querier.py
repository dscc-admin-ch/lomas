from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

from private_dataset.private_dataset import PrivateDataset


class DPQuerier(ABC):
    """
    Overall query to external DP library
    """

    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        """
        Initialise with specific dataset
        """
        self.private_dataset = private_dataset

    @abstractmethod
    def cost(self, query_json: BaseModel) -> List[float]:
        """
        Estimate cost of query
        """

    @abstractmethod
    def query(self, query_json: BaseModel) -> str:
        """
        Does the query and return the response
        """
