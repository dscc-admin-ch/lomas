from typing import Annotated, Dict, List, Literal, Union

import pandas as pd
from diffprivlib.validation import DiffprivlibMixin
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    PlainSerializer,
    PlainValidator,
    ValidationInfo,
    field_validator,
)
from snsynth import Synthesizer

from lomas_core.constants import DPLibraries
from lomas_core.models.utils import (
    dataframe_from_dict,
    dataframe_to_dict,
    deserialize_model,
    serialize_model,
)


class ResponseModel(BaseModel):
    """Base model for any response from the server."""


class InitialBudgetResponse(ResponseModel):
    """Model for responses to initial budget queries."""

    initial_epsilon: float
    initial_delta: float


class SpentBudgetResponse(ResponseModel):
    """Model for responses to spent budget queries."""

    total_spent_epsilon: float
    total_spent_delta: float


class RemainingBudgetResponse(ResponseModel):
    """Model for responses to remaining budget queries."""

    remaining_epsilon: float
    remaining_delta: float


class DummyDsResponse(ResponseModel):
    """Model for responses to dummy dataset requests."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    dtypes: Dict[str, str]
    datetime_columns: List[str]
    dummy_df: Annotated[pd.DataFrame, PlainSerializer(dataframe_to_dict)]

    @field_validator("dummy_df", mode="before")
    @classmethod
    def deserialize_dummy_df(
        cls, v: pd.DataFrame | dict, info: ValidationInfo
    ) -> pd.DataFrame:
        """Decodes the dict representation of the dummy df with correct types.

        Only does so if the input value is not already a dataframe.
        Args:
            v (pd.DataFrame | dict): The dataframe to decode.
            info (ValidationInfo): Validation info to access other model fields.

        Returns:
            pd.DataFrame: The decoded dataframe.
        """
        if isinstance(v, pd.DataFrame):
            return v

        dtypes = info.data["dtypes"]
        datetime_columns = info.data["datetime_columns"]
        dummy_df = dataframe_from_dict(v)
        dummy_df = dummy_df.astype(dtypes)
        for col in datetime_columns:
            dummy_df[col] = pd.to_datetime(dummy_df[col])
        return dummy_df


class CostResponse(ResponseModel):
    """Model for responses to cost estimation requests."""

    epsilon: float
    delta: float


# Query Responses
# -----------------------------------------------------------------------------


# DiffPrivLib
class DiffPrivLibQueryResult(BaseModel):
    """Model for diffprivlib query result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    res_type: Literal[DPLibraries.DIFFPRIVLIB] = DPLibraries.DIFFPRIVLIB
    score: float
    model: Annotated[
        DiffprivlibMixin,
        PlainSerializer(serialize_model),
        PlainValidator(deserialize_model),
    ]


# SmartnoiseSQL
class SmartnoiseSQLQueryResult(BaseModel):
    """Type for smartnoise_sql result type."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    res_type: Literal[DPLibraries.SMARTNOISE_SQL] = DPLibraries.SMARTNOISE_SQL
    df: Annotated[
        pd.DataFrame,
        PlainSerializer(dataframe_to_dict),
        PlainValidator(dataframe_from_dict),
    ]


# SmartnoiseSynth
class SmartnoiseSynthModel(BaseModel):
    """Type for smartnoise_synth result when it is a pickled model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    res_type: Literal[DPLibraries.SMARTNOISE_SYNTH] = DPLibraries.SMARTNOISE_SYNTH
    model: Annotated[
        Synthesizer, PlainSerializer(serialize_model), PlainValidator(deserialize_model)
    ]


class SmartnoiseSynthSamples(BaseModel):
    """Type for smartnoise_synth result when it is a dataframe of samples."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    res_type: Literal["sn_synth_samples"] = "sn_synth_samples"
    df_samples: Annotated[
        pd.DataFrame,
        PlainSerializer(dataframe_to_dict),
        PlainValidator(dataframe_from_dict),
    ]


# OpenDP
class OpenDPQueryResult(BaseModel):
    """Type for opendp result."""

    res_type: Literal[DPLibraries.OPENDP] = DPLibraries.OPENDP
    value: Union[int, float, List[Union[int, float]]]


# Response object
QueryResultTypeAlias = Union[
    DiffPrivLibQueryResult,
    SmartnoiseSQLQueryResult,
    SmartnoiseSynthModel,
    SmartnoiseSynthSamples,
    OpenDPQueryResult,
]


class QueryResponse(CostResponse):
    """Model for responses to queries."""

    requested_by: str
    result: Annotated[
        QueryResultTypeAlias,
        Discriminator("res_type"),
    ]
