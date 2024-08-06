from typing import Optional

from pydantic import BaseModel, Field

from constants import DELTA_LIMIT, EPSILON_LIMIT


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


class OpenDPInp(BaseModel):
    """Model input for an opendp query"""

    dataset_name: str
    opendp_json: str
    pipeline_type: str
    delta: Optional[float] = None
    mechanism: Optional[str] = None


class DummyOpenDPInp(BaseModel):
    """Model input for a dummy opendp query"""

    dataset_name: str
    opendp_json: str
    mechanism: Optional[str] = None
    pipeline_type: str
    dummy_nb_rows: int
    dummy_seed: int
    delta: Optional[float] = None


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
