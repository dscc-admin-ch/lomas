import globals
from typing import List
from pydantic import BaseModel, validator, Field
from utils.constants import EPSILON_LIMIT, DELTA_LIMIT
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


class OpenDPBase(BasicModel):
    function: str
    args: List
    kwargs: dict


class OpenDPAST(BasicModel):
    func: str
    module: str
    type: str
    args: dict = {}
    kwargs: dict = {}


class OpenDPInp(BasicModel):
    # from_function: OpenDPBase
    # to_function: OpenDPBase
    version: str
    ast: OpenDPAST


class DiffPrivLibModel(BasicModel):
    name: str
    type: str

    # Could take single epsilon value and divide by len of pipeline
    # to set epsilon for individual pipeline
    # epsilon: float = Field(..., gt=0, le=10)

    params: dict

    # @validator('type')
    # def validate_model(cls, type):
    #     if type not in diffpriv_map.keys():
    #         raise ValueError(f"'{type}' is not \
    #                one of {list(diffpriv_map.keys())}.")
    #     return type


class DiffPrivLibInp(BasicModel):
    module: str
    pipeline: List[DiffPrivLibModel]
    version: str
    y_column: str

    @validator("y_column")
    def valid_Y(cls, y_column):
        if y_column not in globals.TRAIN_Y.columns:
            raise ValueError(
                f"Provided y value '{y_column}' is not available. \
                    Please select one of {list(globals.TRAIN_Y.columns)}."
            )
        return y_column

    @validator("module")
    def valid_module(cls, module):
        if module != "diffprivlib":
            raise ValueError(f"'{module}' is not diffprivlib.")
        return module


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


class DummySNSQLInp(BasicModel):
    query_str: str
    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int
    epsilon: float
    delta: float


class GetBudgetInp(BaseModel):
    user_name: str
    dataset_name: str
