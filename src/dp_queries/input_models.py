import globals
from typing import List
from pydantic import BaseModel, validator, Field
from smartnoise_json.synth import synth_map
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


class SNSQLInp(BasicModel):
    query_str: str
    epsilon: float = Field(
        ...,
        gt=0,
        le=globals.EPSILON_LIMIT,
    )
    delta: float = Field(
        ...,
        gt=0,
        le=globals.DELTA_LIMIT,
    )


class SNSynthInp(BasicModel):
    model: str
    epsilon: float = Field(
        ...,
        gt=0,
        le=globals.EPSILON_LIMIT,
    )
    delta: float = 0
    select_cols: List = []
    params: dict = {}
    mul_matrix: List = []

    @validator("model")
    def valid_model(cls, model):
        if model not in synth_map.keys():
            raise ValueError(
                f"'{model}' is not one of {list(synth_map.keys())}."
            )
        return model

    @validator("delta")
    def valid_delta(cls, delta, values):
        if values.get("model", "na") not in synth_map.keys():
            raise ValueError(
                f"{values.get('model')} is not \
                    one of {list(synth_map.keys())}."
            )
        if values["model"] != "MWEM" and (
            not delta > 0 or delta > globals.DELTA_LIMIT
        ):
            raise ValueError(
                f"For models other than MWEM delta value should be greater \
                    than 0 and less than or equal to {globals.DELTA_LIMIT}. \
                        User provided: {str(delta)}"
            )
        return delta
