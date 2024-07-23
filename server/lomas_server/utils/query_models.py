from typing import List, Optional

from pydantic import BaseModel, Field, validator

from constants import DELTA_LIMIT, EPSILON_LIMIT, SmartnoiseSynthModels
from utils.error_handler import InvalidQueryException


class GetDbData(BaseModel):
    """Model input to get information about a dataset"""

    dataset_name: str


class GetDummyDataset(BaseModel):
    """Model input to get a dummy dataset"""

    dataset_name: str
    dummy_nb_rows: int = Field(..., gt=0)
    dummy_seed: int


class SmartnoiseSQLModel(BaseModel):
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


class DummySmartnoiseSQLModel(BaseModel):
    """Model input for a smarnoise-sql dummy query"""

    query_str: str
    dataset_name: str
    dummy_nb_rows: int = Field(..., gt=0)
    dummy_seed: int
    epsilon: float = Field(..., gt=0)
    delta: float = Field(..., gt=0)
    mechanisms: dict
    postprocess: bool


class SmartnoiseSQLCostModel(BaseModel):
    """Model input for a smarnoise-sql cost query"""

    query_str: str
    dataset_name: str
    epsilon: float = Field(..., gt=0)
    delta: float = Field(..., gt=0)
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
    nullable: bool = True
    condition: Optional[str] = None
    nb_samples: Optional[int] = None

    @validator("model")
    def valid_model(cls, model):
        """Validate input model"""
        supported_models = [model.value for model in SmartnoiseSynthModels]
        if model not in supported_models:
            raise InvalidQueryException(
                f"'{model}' is not one of {supported_models}."
            )
        return model

    @validator("delta")
    def valid_delta(cls, delta, values):
        """Validate input delta"""
        if values["model"] != SmartnoiseSynthModels.MWEM and (
            not delta > 0 or delta > DELTA_LIMIT
        ):
            raise InvalidQueryException(
                "For models other than MWEM delta value should be greater than 0 and"
                + f" less than or equal to {DELTA_LIMIT}. User provided: {str(delta)}."
            )
        return delta


class OpenDPModel(BaseModel):
    """Model input for an opendp query"""

    dataset_name: str
    opendp_json: str
    fixed_delta: Optional[float] = None


class DummyOpenDPModel(BaseModel):
    """Model input for a dummy opendp query"""

    dataset_name: str
    opendp_json: str
    dummy_nb_rows: int = Field(..., gt=0)
    dummy_seed: int
    fixed_delta: Optional[float] = None


class DiffPrivLibModel(BaseModel):
    """Model input for a diffprivlib query"""

    dataset_name: str
    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float = Field(..., gt=0.0, lt=1.0)
    test_train_split_seed: int
    imputer_strategy: str


class DummyDiffPrivLibModel(BaseModel):
    """Model input for a dummy diffprivlib query"""

    dataset_name: str
    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float = Field(..., gt=0.0, lt=1.0)
    test_train_split_seed: int
    imputer_strategy: str
    dummy_nb_rows: int = Field(..., gt=0)
    dummy_seed: int
