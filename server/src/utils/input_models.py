import json
from typing import Optional

from constants import DELTA_LIMIT, EPSILON_LIMIT
from pydantic import BaseModel, Field


class BasicModel(BaseModel):
    def toJSON(self) -> str:
        return json.loads(
            json.dumps(
                self,
                default=lambda o: (
                    o.__str__()
                    if type(o).__name__ == "datetime"
                    else o.__dict__
                ),
            )
        )

    def toJSONStr(self) -> str:
        return json.dumps(
            self,
            default=lambda o: (
                o.__str__() if type(o).__name__ == "datetime" else o.__dict__
            ),
        )


class GetDbData(BaseModel):
    dataset_name: str


class GetDummyDataset(BasicModel):
    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int


class SNSQLInp(BasicModel):
    query_str: str
    dataset_name: str
    epsilon: float = Field(
        ...,
        gt=0,
        le=EPSILON_LIMIT,
    )
    delta: float = Field(
        ...,
        gt=0,
        le=DELTA_LIMIT,
    )
    mechanisms: dict
    postprocess: bool


class DummySNSQLInp(BasicModel):
    query_str: str
    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int
    epsilon: float
    delta: float
    mechanisms: dict
    postprocess: bool


class SNSQLInpCost(BasicModel):
    query_str: str
    dataset_name: str
    epsilon: float
    delta: float
    mechanisms: dict


class OpenDPInp(BasicModel):
    dataset_name: str
    opendp_json: str
    input_data_type: str
    fixed_delta: Optional[float] = None


class DummyOpenDPInp(BasicModel):
    dataset_name: str
    opendp_json: str
    input_data_type: str
    dummy_nb_rows: int
    dummy_seed: int
    fixed_delta: Optional[float] = None
