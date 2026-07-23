from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from lomas_core.constants import (
    DPLibraries,
)
from lomas_core.models.constants import JSON_SCHEMA_EXAMPLES, PrivateDatabaseType, QueryTypes
from lomas_core.models.requests_examples import (
    EXAMPLE_DIFFPRIVLIB,
    EXAMPLE_DUMMY_DIFFPRIVLIB,
    EXAMPLE_DUMMY_OPENDP,
    EXAMPLE_DUMMY_SMARTNOISE_SQL,
    EXAMPLE_OPENDP_POLARS,
    EXAMPLE_SMARTNOISE_SQL,
    EXAMPLE_SMARTNOISE_SQL_COST,
)


class LomasRequestModel(BaseModel):
    """Base class for all types of requests to the lomas server."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    def model_post_init(self, _: Any) -> None:
        # This makes sure the discriminator field is dumped even with exclude_unset=True
        if "request_type" in self.__class__.model_fields:
            self.model_fields_set.add("response_type")

        if "library" in self.__class__.model_fields:
            self.model_fields_set.add("librray")

    dataset_name: str
    """The name of the dataset the request is aimed at."""


class AddDatasetModel(LomasRequestModel):
    """Model input to add a private dataset with metadata."""

    database_type: PrivateDatabaseType
    """Type of Private Database for the private data."""
    metadata_database_type: PrivateDatabaseType
    """Type of Private Database for the private data."""
    dataset_path: str
    """Path to the dataset."""
    metadata_path: str
    """Path to the metadata."""


class GetDummyDataset(LomasRequestModel):
    """Model input to get a dummy dataset."""

    dummy_nb_rows: Annotated[int, Field(gt=0)]
    """The number of dummy rows to generate."""
    dummy_seed: int
    """The seed for the random generation of the dummy dataset."""


class GetDummyContext(GetDummyDataset):
    """Model input to get a dummy dataset."""

    epsilon: Annotated[float | None, Field(ge=0.0)]
    """The epsilon parameter used for pure ε-DP or approximate-DP."""
    delta: Annotated[float | None, Field(ge=0.0)]
    """The delta parameter."""
    rho: Annotated[float | None, Field(ge=0.0)]
    """
    Privacy loss paramater for zCDP (or approximate-zCDP).

    Using this parameter instead of `epsilon` switches to a Gaussian mechansim.
    """
    approx_zcdp: bool
    """If False, delta is used to compute the epsilon consumption equivalent when user wants to use zCDP."""


class QueryModel(LomasRequestModel):
    """Base input model for any query on a dataset."""

    request_type: Literal[QueryTypes.QUERY] = QueryTypes.QUERY


class CostQueryModel(LomasRequestModel):
    """Base input model for a cost query."""

    request_type: Literal[QueryTypes.COST] = QueryTypes.COST


class LomasBudgetRequest(LomasRequestModel):
    epsilon: Annotated[float, Field(gt=0)]
    """Privacy parameter (e.g., 0.1)."""
    delta: Annotated[float, Field(ge=0)]
    """Privacy parameter (e.g., 1e-5)."""


class DummyQueryModel(QueryModel):
    """Base input model for a query on a dummy dataset."""

    dummy_nb_rows: Annotated[int, Field(gt=0)]
    """The number of rows in the dummy dataset."""
    dummy_seed: int
    """The seed to set at the start of the dummy dataset generation."""


# SmartnoiseSQL
# ----------------------------------------------------------------------------
class SmartnoiseSQLRequestModel(LomasRequestModel):
    """Base input model for a smarnoise-sql request."""

    library: Literal[DPLibraries.SMARTNOISE_SQL] = DPLibraries.SMARTNOISE_SQL

    query_str: str
    """The SQL query to execute.

    NOTE: the table name is \"df\", the query must end with \"FROM df\"
    """
    epsilon: Annotated[float, Field(gt=0)]
    """Privacy parameter (e.g., 0.1)."""
    delta: Annotated[float, Field(ge=0)]
    """Privacy parameter (e.g., 1e-5)."""
    mechanisms: dict
    """
    Dictionary of mechanisms for the query.

    See Smartnoise-SQL mechanisms documentation at
    https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.
    """


class SmartnoiseSQLCostQueryModel(SmartnoiseSQLRequestModel, CostQueryModel):
    """Base input model for a smartnoise-sql cost query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_SMARTNOISE_SQL_COST]})


class SmartnoiseSQLQueryModel(SmartnoiseSQLRequestModel, QueryModel):
    """Base input model for a smartnoise-sql query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_SMARTNOISE_SQL]})

    postprocess: bool
    """
    Whether to postprocess the query results (default: True).

    See Smartnoise-SQL postprocessing documentation
    https://docs.smartnoise.org/sql/advanced.html#postprocess.
    """


class SmartnoiseSQLDummyQueryModel(SmartnoiseSQLQueryModel, DummyQueryModel):
    """Input model for a smartnoise-sql query on a dummy dataset."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_DUMMY_SMARTNOISE_SQL]})

    # Avoid conflict between QueryModel and DummyQueryMdoel
    request_type: Literal[QueryTypes.DUMMY] = QueryTypes.DUMMY  # type: ignore[assignment]


# OpenDP
# ----------------------------------------------------------------------------
class OpenDPRequestModel(LomasRequestModel):
    """Base input model for an opendp request."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    library: Literal[DPLibraries.OPENDP] = DPLibraries.OPENDP

    opendp_json: str
    """The OpenDP pipeline for the query."""
    epsilon: Annotated[float | None, Field(ge=0)]
    """The epsilon parameter used for pure ε-DP or approximate-DP."""
    delta: Annotated[float | None, Field(ge=0)]
    """
    If the pipeline measurement is of type "ZeroConcentratedDivergence".

    (e.g. with "make_gaussian") then it is converted to "SmoothedMaxDivergence"
    with "make_zCDP_to_approxDP" (see "opendp measurements documentation at
    https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP).
    In that case a "delta" must be provided by the user.
    """
    rho: Annotated[float | None, Field(ge=0)]
    """
    Privacy loss parameter for zCDP (or approximate zCDP).

    Using this parameter instead of `epsilon` switches to a Gaussian mechansim.
    """

    approx_zcdp: bool
    """If false, delta is used to compute the epsilon consumption equivalent when user wants to use zCDP."""

    @model_validator(mode="after")
    def check_epsilon_or_rho(self) -> Self:
        if (self.epsilon is None and self.rho is None) or (self.epsilon and self.rho):
            raise ValueError("Either `epsilon` or `rho` must be set.")
        return self


class OpenDPCostQueryModel(OpenDPRequestModel, CostQueryModel):
    """Base input model for an opendp cost query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_OPENDP_POLARS]})


class OpenDPQueryModel(OpenDPRequestModel, QueryModel):
    """Base input model for an opendp query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_OPENDP_POLARS]})


class OpenDPDummyQueryModel(OpenDPRequestModel, DummyQueryModel):
    """Input model for an opendp query on a dummy dataset."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_DUMMY_OPENDP]})

    # Avoid conflict between QueryModel and DummyQueryMdoel
    request_type: Literal[QueryTypes.DUMMY] = QueryTypes.DUMMY  # type: ignore[assignment]


# DiffPrivLib
# ----------------------------------------------------------------------------
class DiffPrivLibRequestModel(LomasRequestModel):
    """Base input model for a diffprivlib request."""

    library: Literal[DPLibraries.DIFFPRIVLIB] = DPLibraries.DIFFPRIVLIB

    diffprivlib_json: str
    """The DiffPrivLib pipeline for the query (See diffprivlib_logger package.)."""
    feature_columns: list
    """The list of feature columns to train."""
    target_columns: list | None
    """The list of target columns to predict."""
    test_size: Annotated[float, Field(gt=0.0, lt=1.0)]
    """The proportion of the test set."""
    test_train_split_seed: int
    """The seed for the random train/test split."""
    imputer_strategy: str
    """The imputation strategy."""


class DiffPrivLibCostQueryModel(DiffPrivLibRequestModel, CostQueryModel):
    """Base input model for a diffprivlib cost query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_DIFFPRIVLIB]})


class DiffPrivLibQueryModel(DiffPrivLibRequestModel, QueryModel):
    """Base input model for a diffprivlib query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_DIFFPRIVLIB]})


class DiffPrivLibDummyQueryModel(DiffPrivLibQueryModel, DummyQueryModel):
    """Input model for a DiffPrivLib query on a dummy dataset."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [EXAMPLE_DUMMY_DIFFPRIVLIB]})

    # Avoid conflict between QueryModel and DummyQueryMdoel
    request_type: Literal[QueryTypes.DUMMY] = QueryTypes.DUMMY  # type: ignore[assignment]


# Utils
# ----------------------------------------------------------------------------

SmartnoiseSQLAnyModel = Annotated[
    SmartnoiseSQLCostQueryModel | SmartnoiseSQLQueryModel | SmartnoiseSQLDummyQueryModel,
    Field(discriminator="request_type"),
]

OpenDPAnyModel = Annotated[
    OpenDPCostQueryModel | OpenDPQueryModel | OpenDPDummyQueryModel,
    Field(discriminator="request_type"),
]

DiffPrivLibAnyModel = Annotated[
    DiffPrivLibCostQueryModel | DiffPrivLibQueryModel | DiffPrivLibDummyQueryModel,
    Field(discriminator="request_type"),
]

AnyLomasRequest = Annotated[
    SmartnoiseSQLAnyModel | OpenDPAnyModel | DiffPrivLibAnyModel,
    Field(discriminator="library"),
]

LomasRequestAdapter: TypeAdapter[AnyLomasRequest] = TypeAdapter(AnyLomasRequest)
