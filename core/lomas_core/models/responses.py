from datetime import datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID, uuid4

import pandas as pd
import polars as pl
from diffprivlib.validation import DiffprivlibMixin
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    PlainSerializer,
    PlainValidator,
    TypeAdapter,
    ValidationInfo,
    field_validator,
)

from lomas_core.constants import DPLibraries
from lomas_core.models.constants import JobStatus, QueryResponseTypes
from lomas_core.models.exceptions import LomasAPIErrorModel
from lomas_core.models.requests import AnyLomasRequest
from lomas_core.models.utils import (
    dataframe_from_dict,
    dataframe_to_dict,
    deserialize_model,
    polars_df_from_str,
    polars_df_to_str,
    serialize_model,
)


class ResponseModel(BaseModel):
    """Base model for any response from the server."""


class DummyDsResponse(ResponseModel):
    """Model for responses to dummy dataset requests."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dtypes: Any
    """The dummy_df column data types."""
    dummy_df: Annotated[pd.DataFrame, PlainSerializer(dataframe_to_dict), PlainValidator(dataframe_from_dict)]

    """The dummy dataframe."""

    @field_validator("dummy_df", mode="before")
    @classmethod
    def deserialize_dummy_df(cls, v: pd.DataFrame | dict, info: ValidationInfo) -> pd.DataFrame:
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
        dummy_df = dataframe_from_dict(v)
        dummy_df = dummy_df.astype(dtypes)
        return dummy_df


class Budget(ResponseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

    epsilon: float
    """The epsilon cost of the query."""
    delta: float
    """The delta cost of the query."""

    @classmethod
    def zero(cls) -> Self:
        return cls(epsilon=0.0, delta=0.0)

    def __add__(self, other: Self) -> Self:
        return Budget(epsilon=(self.epsilon + other.epsilon), delta=(self.delta + other.delta))

    def __sub__(self, other: Self) -> Self:
        return Budget(epsilon=(self.epsilon - other.epsilon), delta=(self.delta - other.delta))

    # Partial Ordering
    def __lt__(self, other: Self) -> bool:
        return self.epsilon < other.epsilon and self.delta < other.delta

    # this is not the same as a < b and a == b !
    def __le__(self, other: Self) -> bool:
        return self.epsilon <= other.epsilon and self.delta <= other.delta


class CostResponse(Budget):
    """Model for responses to cost estimation requests or queries."""

    response_type: Literal[QueryResponseTypes.COST] = QueryResponseTypes.COST

    def model_post_init(self, _: Any) -> None:
        # This makes sure the discriminator field is dumped even with exclude_unset=True
        if "response_type" in self.__class__.model_fields:
            self.model_fields_set.add("response_type")


# Query Responses
# -----------------------------------------------------------------------------


class QueryResult(BaseModel):
    """Base class for query results."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, _: Any) -> None:
        # This makes sure the discriminator field is dumped even with exclude_unset=True
        if "type" in self.__class__.model_fields:
            self.model_fields_set.add("type")


# DiffPrivLib
class DiffPrivLibQueryResult(QueryResult):
    """Model for diffprivlib query result."""

    type: Literal[DPLibraries.DIFFPRIVLIB] = DPLibraries.DIFFPRIVLIB
    """Result type description."""
    score: float
    """The trained model score."""
    model: Annotated[
        DiffprivlibMixin,
        PlainSerializer(serialize_model),
        PlainValidator(deserialize_model),
    ]
    """The trained model."""


# SmartnoiseSQL
class SmartnoiseSQLQueryResult(QueryResult):
    """Type for smartnoise_sql result type."""

    type: Literal[DPLibraries.SMARTNOISE_SQL] = DPLibraries.SMARTNOISE_SQL
    """Result type description."""
    df: Annotated[
        pd.DataFrame,
        PlainSerializer(dataframe_to_dict),
        PlainValidator(dataframe_from_dict),
    ]
    """Dataframe containing the query result."""


# OpenDP
class OpenDPQueryResult(QueryResult):
    """Type for opendp result."""

    type: Literal[DPLibraries.OPENDP] = DPLibraries.OPENDP
    """Result type description."""
    value: int | float | list[int | float]
    """The result value of the query."""


class OpenDPPolarsQueryResult(QueryResult):
    """Type for opendp Polars result."""

    type: Literal[DPLibraries.OPENDP_POLARS] = DPLibraries.OPENDP_POLARS
    """Result type description."""
    # order of PlainValidator and PlainSerializer matters in that case:
    # https://github.com/pydantic/pydantic/issues/8512
    value: Annotated[
        pl.DataFrame,
        PlainValidator(polars_df_from_str),
        PlainSerializer(polars_df_to_str),
    ]
    """The result value of the query."""


# Response object
QueryResultT = Annotated[
    DiffPrivLibQueryResult | SmartnoiseSQLQueryResult | OpenDPQueryResult | OpenDPPolarsQueryResult,
    Discriminator("type"),
]


class QueryResponse(CostResponse):
    """Response to Lomas queries."""

    response_type: Literal[QueryResponseTypes.QUERY] = QueryResponseTypes.QUERY  # type: ignore[assignment]

    requested_by: str
    """The user that triggered the query."""
    result: QueryResultT
    """The query result object."""


AnyLomasQueryResponse = Annotated[
    CostResponse | QueryResponse,
    Field(discriminator="response_type"),
]

LomasQueryResponseAdapter: TypeAdapter[AnyLomasQueryResponse] = TypeAdapter(AnyLomasQueryResponse)


class Job(ResponseModel):
    """Scheduled Job."""

    uid: UUID = Field(default_factory=uuid4)
    """Job unique identifier."""
    requested_by: str
    """Name of the user that requested this job."""
    dataset_name: str
    """Name of the dataset targetted by this job."""
    status: JobStatus = JobStatus.PENDING
    """Job status."""
    query: AnyLomasRequest
    """Job query."""
    result: AnyLomasQueryResponse | None = None
    """Job result, if available."""
    error: LomasAPIErrorModel | None = None
    """Job error, if any."""
    status_code: int = 200
    """Status code for job response."""
    archived_at: datetime | None = None
    """Time of archive."""
