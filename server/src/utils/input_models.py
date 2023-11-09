# from typing import List
from pydantic import BaseModel, Field
from typing import List, Union, Optional
from constants import EPSILON_LIMIT, DELTA_LIMIT
import json


class BasicModel(BaseModel):
    def toJSON(self):
        return json.loads(
            json.dumps(
                self,
                default=lambda o: o.__str__()
                if type(o).__name__ == "datetime"
                else o.__dict__,
            )
        )

    def toJSONStr(self):
        return json.dumps(
            self,
            default=lambda o: o.__str__()
            if type(o).__name__ == "datetime"
            else o.__dict__,
        )


class GetDatasetMetadata(BasicModel):
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


class GetDbData(BaseModel):
    dataset_name: str


class Transformation(BasicModel):
    _type: str
    func: str
    module: str = "transformations"
    args: Optional[List[dict]]
    kwargs: Optional[dict]


class Measurement(BasicModel):
    _type: str
    func: str
    module: str = "measurements"
    args: Optional[List[dict]]
    kwargs: Optional[dict]


class OpenDPPartialChain(BasicModel):
    _type: str
    lhs: Union['OpenDPPartialChain', Transformation, Measurement]
    rhs: Union['OpenDPPartialChain', Transformation, Measurement]

    @classmethod
    def update_forward_refs(cls):
        super().update_forward_refs()


class OpenDPPipeline(BasicModel):
    version: str
    ast: OpenDPPartialChain
    # ast: dict


class OpenDPInp(BasicModel):
    dataset_name: str
    opendp_json: OpenDPPipeline
    input_data_type: str


class DummyOpenDPInp(BasicModel):
    dataset_name: str
    opendp_json: OpenDPPipeline
    input_data_type: str
    dummy_nb_rows: int
    dummy_seed: int

OpenDPPartialChain.update_forward_refs()
OpenDPPipeline.update_forward_refs()
OpenDPInp.update_forward_refs()
DummyOpenDPInp.update_forward_refs()
