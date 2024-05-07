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
        """_summary_

        Args:
            private_dataset (PrivateDataset): _description_
        """
        self.private_dataset = private_dataset

    @abstractmethod
    def cost(self, query_json: JSON) -> List[float]:
        """_summary_

        Args:
            query_json (JSON): _description_

        Returns:
            List[float]: _description_
        """
        pass

    @abstractmethod
    def query(self, query_json: JSON) -> str:
        """_summary_

        Args:
            query_json (JSON): _description_

        Returns:
            str: _description_
        """
        pass
