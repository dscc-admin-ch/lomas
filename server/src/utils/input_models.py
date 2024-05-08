from typing import Optional

from pydantic import BaseModel, Field

from constants import DELTA_LIMIT, EPSILON_LIMIT


class GetDbData(BaseModel):
    dataset_name: str


class GetDummyDataset(BaseModel):
    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int


class SNSQLInp(BaseModel):
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


class DummySNSQLInp(BaseModel):
    query_str: str
    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int
    epsilon: float
    delta: float
    mechanisms: dict
    postprocess: bool


class SNSQLInpCost(BaseModel):
    query_str: str
    dataset_name: str
    epsilon: float
    delta: float
    mechanisms: dict


class OpenDPInp(BaseModel):
    dataset_name: str
    opendp_json: str
    fixed_delta: Optional[float] = None


class DummyOpenDPInp(BaseModel):
    dataset_name: str
    opendp_json: str
    dummy_nb_rows: int
    dummy_seed: int
    fixed_delta: Optional[float] = None
