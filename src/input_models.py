from datetime import datetime
from typing import List, Any
from pydantic import BaseModel, validator, Field
from diffprivlib_json.diffprivl import diffpriv_map
from smartnoise_json.synth import synth_map
import json


class BasicModel(BaseModel):
    def toJSON(self):
        return json.loads(json.dumps(self, default=lambda o: o.__str__() if type(o).__name__ == "datetime" else o.__dict__))

    def toJSONStr(self):
        return json.dumps(self, default=lambda o: o.__str__() if type(o).__name__ == "datetime" else o.__dict__)

class OpenDPBase(BasicModel):
    function: str
    args: List
    kwargs: dict


class OpenDPAST(BasicModel):
    func: str
    module: str
    type: str
    args: List = []
    kwargs: dict = {}

    
class OpenDPInp(BasicModel):
    # from_function: OpenDPBase
    # to_function: OpenDPBase
    version: str
    ast: OpenDPAST

    
# version: 0.3.0
# ast:
#   func: make_chain_tt
#   module: comb
#   type: Transformation
#   args:
#   - func: make_select_column
#   module: trans
#   type: Transformation
#   args: []
#   kwargs:
#       key: income
#       TOA: py_type: str
#   - func: make_split_dataframe
#   module: trans
#   type: Transformation
#   args: []
#   kwargs:
#       separator: ","
#       col_names:
#       - hello
#       - world
#   kwargs: {}


class DiffPrivLibModel(BasicModel):
    name: str
    model: str 
    # epsilon: float = Field(..., gt=0, le=10) #Could take single epsilon value and divide by len of pipeline to set epsilon for individual pipeline
    args: List
    kwargs: dict
    
    @validator('model')
    def validate_model(cls, model):
        if model not in diffpriv_map.keys():
            raise ValueError(f"'{model}' is not one of {list(diffpriv_map.keys())}.")
        return model
    
    @validator('kwargs')
    def validate_epsilon(cls, kwargs):
        return kwargs


class DiffPrivLibInp(BasicModel):
    pipeline: List[DiffPrivLibModel]
    version: str


class SNSQLInp(BasicModel):
    query_str: str
    epsilon: float = Field(..., gt=0, le=10)
    delta: float = 0

 
class SNSynthInp(BasicModel):
    model: str
    epsilon: float = Field(..., gt=0, le=10)
    params: dict = {}

    @validator('model')
    def valid_model(cls, model):
        if model not in synth_map.keys():
            raise ValueError(f"'{model}' is not one of {list(synth_map.keys())}.")
        return model



# ast:
#   from:
#     args: !!python/tuple []
#     func: make_split_dataframe
#     kwargs:
#       col_names:
#       - hello
#       - world
#       separator: ','
#     type: Transformation
#   to:
#     args: !!python/tuple []
#     func: make_select_column
#     kwargs:
#       TOA: !!python/name:builtins.str ''
#       key: income
#     type: Transformation
# version: 0.5.0
