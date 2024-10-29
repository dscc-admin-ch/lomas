from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from lomas_core.constants import (
    DPLibraries,
    SSynthGanSynthesizer,
    SSynthMarginalSynthesizer,
)
from lomas_core.error_handler import InternalServerException


class LomasRequestModel(BaseModel):
    """Base class for all types of requests to the lomas server.

    We differentiate between requests and queries:
        - a request does not necessarily require an algorithm
          to be executed on the private dataset (e.g. some cost requests).
        - a query requires executing an algorithm on a private
          dataset (or a potentially a dummy).
    """

    dataset_name: str


class GetDummyDataset(LomasRequestModel):
    """Model input to get a dummy dataset."""

    dummy_nb_rows: int = Field(..., gt=0)
    dummy_seed: int


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
    dummy_seed: int


# SmartnoiseSQL
# ----------------------------------------------------------------------------
class SmartnoiseSQLRequestModel(LomasRequestModel):
    """Base input model for a smarnoise-sql request."""

    query_str: str
    epsilon: float = Field(..., gt=0)
    delta: float = Field(..., gt=0)
    mechanisms: dict


class SmartnoiseSQLQueryModel(SmartnoiseSQLRequestModel, QueryModel):
    """Base input model for a smartnoise-sql query."""

    postprocess: bool


class SmartnoiseSQLDummyQueryModel(SmartnoiseSQLQueryModel, DummyQueryModel):
    """Input model for a smartnoise-sql query on a dummy dataset."""


# SmartnoiseSynth
# ----------------------------------------------------------------------------
class SmartnoiseSynthRequestModel(LomasRequestModel):
    """Base input model for a SmartnoiseSynth request."""

    synth_name: Union[SSynthMarginalSynthesizer, SSynthGanSynthesizer]
    epsilon: float = Field(..., gt=0)
    delta: Optional[float] = None
    select_cols: List
    synth_params: dict
    nullable: bool
    constraints: str


class SmartnoiseSynthQueryModel(SmartnoiseSynthRequestModel, QueryModel):
    """Base input model for a smarnoise-synth query."""

    return_model: bool
    condition: str
    nb_samples: int


class SmartnoiseSynthDummyQueryModel(SmartnoiseSynthQueryModel, DummyQueryModel):
    """Input model for a smarnoise-synth query on a dummy dataset."""

    # Same as normal query.
    return_model: bool
    condition: str
    nb_samples: int


# OpenDP
# ----------------------------------------------------------------------------
class OpenDPRequestModel(LomasRequestModel):
    """Base input model for an opendp request."""

    model_config = ConfigDict(use_attribute_docstrings=True)
    opendp_json: str
    """Opendp pipeline."""
    fixed_delta: Optional[float] = None


class OpenDPQueryModel(OpenDPRequestModel, QueryModel):
    """Base input model for an opendp query."""


class OpenDPDummyQueryModel(OpenDPRequestModel, DummyQueryModel):
    """Input model for an opendp query on a dummy dataset."""


# DiffPrivLib
# ----------------------------------------------------------------------------
class DiffPrivLibRequestModel(LomasRequestModel):
    """Base input model for a diffprivlib request."""

    diffprivlib_json: str
    feature_columns: list
    target_columns: Optional[list]
    test_size: float = Field(..., gt=0.0, lt=1.0)
    test_train_split_seed: int
    imputer_strategy: str


class DiffPrivLibQueryModel(DiffPrivLibRequestModel, QueryModel):
    """Base input model for a diffprivlib query."""


class DiffPrivLibDummyQueryModel(DiffPrivLibQueryModel, DummyQueryModel):
    """Input model for a DiffPrivLib query on a dummy dataset."""


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
