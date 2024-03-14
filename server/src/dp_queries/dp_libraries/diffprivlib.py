from typing import List
from fastapi import HTTPException

from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset

class DiffPrivLibQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: dict) -> List[float]:

        return 0, 0

    def query(self, query_json: dict) -> str:

        return 0