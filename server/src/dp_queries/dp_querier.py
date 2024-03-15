from abc import ABC, abstractmethod
from typing import List

from constants import LIB_DIFFPRIVLIB, LIB_OPENDP, LIB_SMARTNOISE_SQL
from dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from dp_queries.dp_libraries.open_dp import OpenDPQuerier
from dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
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


def querier_factory(lib, private_dataset):
    if lib == LIB_SMARTNOISE_SQL:
        querier = SmartnoiseSQLQuerier(private_dataset)
        
    elif lib == LIB_OPENDP:
        querier = OpenDPQuerier(private_dataset)
        
    elif lib == LIB_DIFFPRIVLIB:
        querier = DiffPrivLibQuerier(private_dataset)

    else:
        raise Exception(
            f"Trying to create a querier for library {lib}. "
            "This should never happen."
        )
    return querier