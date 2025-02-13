from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from lomas_core.constants import (
    DPLibraries,
    SSynthGanSynthesizer,
    SSynthMarginalSynthesizer,
)
from lomas_core.error_handler import InternalServerException
from lomas_core.models.constants import JSON_SCHEMA_EXAMPLES
from lomas_core.models.requests_examples import (
    example_diffprivlib,
    example_dummy_diffprivlib,
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_dummy_smartnoise_synth_query,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
    example_smartnoise_synth_cost,
    example_smartnoise_synth_query,
)


class LomasRequestModel(BaseModel):
    """Base class for all types of requests to the lomas server.

    We differentiate between requests and queries:
        - a request does not necessarily require an algorithm
          to be executed on the private dataset (e.g. some cost requests).
        - a query requires executing an algorithm on a private
          dataset (or a potentially a dummy).
    """

    model_config = ConfigDict(use_attribute_docstrings=True)
    dataset_name: str
    """The name of the dataset the request is aimed at."""


class GetDummyDataset(LomasRequestModel):
    """Model input to get a dummy dataset."""

    dummy_nb_rows: int = Field(..., gt=0)
    """The number of dummy rows to generate."""
    dummy_seed: int
    """The seed for the random generation of the dummy dataset."""


class QueryModel(LomasRequestModel):
    """
    Base input model for any query on a dataset.

    We differentiate between requests and queries:
        - a request does not necessarily require an algorithm
          to be executed on the private dataset (e.g. some cost requests).
        - a query requires executing an algorithm on a private
          dataset (or a potentially a dummy).
    """


class DummyQueryModel(QueryModel):
    """Input model for a query on a dummy dataset."""

    dummy_nb_rows: int = Field(..., gt=0)
    """The number of rows in the dummy dataset."""
    dummy_seed: int
    """The seed to set at the start of the dummy dataset generation."""


# SmartnoiseSQL
# ----------------------------------------------------------------------------
class SmartnoiseSQLRequestModel(LomasRequestModel):
    """Base input model for a smarnoise-sql request."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_smartnoise_sql_cost]})

    query_str: str
    """The SQL query to execute.

    NOTE: the table name is \"df\", the query must end with \"FROM df\"
    """
    epsilon: float = Field(..., gt=0)
    """Privacy parameter (e.g., 0.1)."""
    delta: float = Field(..., ge=0)
    """Privacy parameter (e.g., 1e-5)."""
    mechanisms: dict
    """
    Dictionary of mechanisms for the query.

    See Smartnoise-SQL mechanisms documentation at
    https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.
    """


class SmartnoiseSQLQueryModel(SmartnoiseSQLRequestModel, QueryModel):
    """Base input model for a smartnoise-sql query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_smartnoise_sql]})

    postprocess: bool
    """
    Whether to postprocess the query results (default: True).

    See Smartnoise-SQL postprocessing documentation
    https://docs.smartnoise.org/sql/advanced.html#postprocess.
    """


class SmartnoiseSQLDummyQueryModel(SmartnoiseSQLQueryModel, DummyQueryModel):
    """Input model for a smartnoise-sql query on a dummy dataset."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_dummy_smartnoise_sql]})


# SmartnoiseSynth
# ----------------------------------------------------------------------------
class SmartnoiseSynthRequestModel(LomasRequestModel):
    """Base input model for a SmartnoiseSynth request."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_smartnoise_synth_cost]})

    synth_name: Union[SSynthMarginalSynthesizer, SSynthGanSynthesizer]
    """Name of the synthesizer model to use."""
    epsilon: float = Field(..., gt=0)
    """Privacy parameter (e.g., 0.1)."""
    delta: Optional[float] = Field(..., ge=0)
    """Privacy parameter (e.g., 1e-5)."""
    select_cols: List
    """List of columns to select."""
    synth_params: dict
    """
    Keyword arguments to pass to the synthesizer constructor.

    See https://docs.smartnoise.org/synth/synthesizers/index.html#, provide
    all parameters of the model except `epsilon` and `delta`.
    """
    nullable: bool
    """True if some data cells may be null."""
    constraints: str
    """
    Dictionnary for custom table transformer constraints.

    Column that are not specified will be inferred based on metadata.
    """


class SmartnoiseSynthQueryModel(SmartnoiseSynthRequestModel, QueryModel):
    """Base input model for a smarnoise-synth query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_smartnoise_synth_query]})

    return_model: bool
    """True to get Synthesizer model, False to get samples."""
    condition: str
    """Sampling condition in `model.sample` (only relevant if return_model is False)."""
    nb_samples: int
    """Number of samples to generate.

    (only relevant if return_model is False)
    """


class SmartnoiseSynthDummyQueryModel(SmartnoiseSynthQueryModel, DummyQueryModel):
    """Input model for a smarnoise-synth query on a dummy dataset."""

    model_config = ConfigDict(
        json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_dummy_smartnoise_synth_query]}
    )


# OpenDP
# ----------------------------------------------------------------------------
class OpenDPRequestModel(LomasRequestModel):
    """Base input model for an opendp request."""

    model_config = ConfigDict(
        use_attribute_docstrings=True,
        json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_opendp]},
    )

    opendp_json: str
    """The OpenDP pipeline for the query."""
    fixed_delta: Optional[float] = Field(..., ge=0)
    """
    If the pipeline measurement is of type "ZeroConcentratedDivergence".

    (e.g. with "make_gaussian") then it is converted to "SmoothedMaxDivergence"
    with "make_zCDP_to_approxDP" (see "opendp measurements documentation at
    https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP). # noqa # pylint: disable=C0301
    In that case a "fixed_delta" must be provided by the user.
    """


class OpenDPQueryModel(OpenDPRequestModel, QueryModel):
    """Base input model for an opendp query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_opendp]})


class OpenDPDummyQueryModel(OpenDPRequestModel, DummyQueryModel):
    """Input model for an opendp query on a dummy dataset."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_dummy_opendp]})


# DiffPrivLib
# ----------------------------------------------------------------------------
class DiffPrivLibRequestModel(LomasRequestModel):
    """Base input model for a diffprivlib request."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_diffprivlib]})

    diffprivlib_json: str
    """The DiffPrivLib pipeline for the query (See diffprivlib_logger package.)."""
    feature_columns: list
    """The list of feature columns to train."""
    target_columns: Optional[list]
    """The list of target columns to predict."""
    test_size: float = Field(..., gt=0.0, lt=1.0)
    """The proportion of the test set."""
    test_train_split_seed: int
    """The seed for the random train/test split."""
    imputer_strategy: str
    """The imputation strategy."""


class DiffPrivLibQueryModel(DiffPrivLibRequestModel, QueryModel):
    """Base input model for a diffprivlib query."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_diffprivlib]})


class DiffPrivLibDummyQueryModel(DiffPrivLibQueryModel, DummyQueryModel):
    """Input model for a DiffPrivLib query on a dummy dataset."""

    model_config = ConfigDict(json_schema_extra={JSON_SCHEMA_EXAMPLES: [example_dummy_diffprivlib]})


# Utils
# ----------------------------------------------------------------------------


def model_input_to_lib(request: LomasRequestModel) -> DPLibraries:
    """Return the type of DP library given a LomasRequestModel.

    Args:
        request (LomasRequestModel): The user request

    Raises:
        InternalServerException: If the library type cannot be determined.

    Returns:
        DPLibraries: The type of library for the request.
    """
    match request:
        case SmartnoiseSQLRequestModel():
            return DPLibraries.SMARTNOISE_SQL
        case SmartnoiseSynthRequestModel():
            return DPLibraries.SMARTNOISE_SYNTH
        case OpenDPRequestModel():
            return DPLibraries.OPENDP
        case DiffPrivLibRequestModel():
            return DPLibraries.DIFFPRIVLIB
        case _:
            raise InternalServerException("Cannot find library type for given model.")
