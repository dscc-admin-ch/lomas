from pydantic import BaseModel, Field
from typing import Optional
from constants import EPSILON_LIMIT, DELTA_LIMIT
import json


class BasicModel(BaseModel):
    def toJSON(self):
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

    def toJSONStr(self):
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


class DummyOpenDPInp(BasicModel):
    dataset_name: str
    opendp_json: str
    input_data_type: str
    dummy_nb_rows: int
    dummy_seed: int


# class DiffPrivLibCost(BasicModel):
#     dataset_name: str
#     diffprivlib_json: str
#     feature_columns: list
#     target_columns: list


class DiffPrivLibInp(BasicModel):
    dataset_name: str
    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float
    test_train_split_seed: int
    imputer_strategy: str


class DummyDiffPrivLibInp(BasicModel):
    dataset_name: str
    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float
    test_train_split_seed: int
    imputer_strategy: str
    dummy_nb_rows: int
    dummy_seed: int
