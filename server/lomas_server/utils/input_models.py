from typing import List, Optional

from pydantic import BaseModel, validator, Field

from constants import DELTA_LIMIT, EPSILON_LIMIT, SmartnoiseSynthModels

from utils.error_handler import InvalidQueryException


class GetDbData(BaseModel):
    """Model input to get information about a dataset"""

    dataset_name: str


class GetDummyDataset(BaseModel):
    """Model input to get a dummy dataset"""

    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int


class SNSQLInp(BaseModel):
    """Model input for a smarnoise-sql query"""

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
    """Model input for a smarnoise-sql dummy query"""

    query_str: str
    dataset_name: str
    dummy_nb_rows: int
    dummy_seed: int
    epsilon: float
    delta: float
    mechanisms: dict
    postprocess: bool


class SNSQLInpCost(BaseModel):
    """Model input for a smarnoise-sql cost query"""

    query_str: str
    dataset_name: str
    epsilon: float
    delta: float
    mechanisms: dict


class SmartnoiseSynthModel(BaseModel):
    """Model input for a smarnoise-synth query"""

    dataset_name: str
    model: str
    epsilon: float = Field(..., gt=0, le=EPSILON_LIMIT)
    delta: float = 0.0
    select_cols: List = []
    params: dict = {}
    mul_matrix: List = []

    @validator("model")
    def valid_model(cls, model):
        supported_models = [model.value for model in SmartnoiseSynthModels]
        if model not in supported_models:
            raise InvalidQueryException(
                f"'{model}' is not one of {supported_models}."
            )
        return model

    @validator("delta")
    def valid_delta(cls, delta, values):
        if values["model"] != SmartnoiseSynthModels.MWEM and (
            not delta > 0 or delta > DELTA_LIMIT
        ):
            raise InvalidQueryException(
                "For models other than MWEM delta value should be greater than 0 and"
                + f" less than or equal to {DELTA_LIMIT}. User provided: {str(delta)}."
            )
        return delta


class OpenDPInp(BaseModel):
    """Model input for an opendp query"""

    dataset_name: str
    opendp_json: str
    fixed_delta: Optional[float] = None


class DummyOpenDPInp(BaseModel):
    """Model input for a dummy opendp query"""

    dataset_name: str
    opendp_json: str
    dummy_nb_rows: int
    dummy_seed: int
    fixed_delta: Optional[float] = None


class DiffPrivLibInp(BaseModel):
    """Model input for a diffprivlib query"""

    dataset_name: str
    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float
    test_train_split_seed: int
    imputer_strategy: str


class DummyDiffPrivLibInp(BaseModel):
    """Model input for a dummy diffprivlib query"""

    dataset_name: str
    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float
    test_train_split_seed: int
    imputer_strategy: str
    dummy_nb_rows: int
    dummy_seed: int
