from abc import ABC, abstractmethod
from typing import List, TypeAlias

from private_dataset.private_dataset import PrivateDataset

# https://stackoverflow.com/questions/51291722/define-a-jsonable-type-using-mypy-pep-526
JSON: TypeAlias = (
    dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
)


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
    def cost(self, query_json: JSON) -> List[float]:
        """
        Estimate cost of query
        """

    @abstractmethod
    def query(self, query_json: JSON) -> str:
        """
        Does the query and return the response
        """
