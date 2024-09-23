from typing import List, Optional, Union

from lomas_core.constants import (
    DPLibraries,
    SSynthGanSynthesizer,
    SSynthMarginalSynthesizer,
)
from lomas_core.error_handler import InternalServerException
from pydantic import BaseModel, Field


class GetDbData(BaseModel):
    """Model input to get information about a dataset."""

    dataset_name: str


class GetDummyDataset(BaseModel):
    """Model input to get a dummy dataset."""

    dataset_name: str
    dummy_nb_rows: int = Field(..., gt=0)
    dummy_seed: int


class RequestModel(BaseModel):
    """
    Base input model for any request on a dataset.

    We differentiate between requests and queries:
        - a request does not necessarily require an algorithm
          to be executed on the private dataset (e.g. some cost requests).
        - a query requires executing an algorithm on a private
          dataset (or a potentially a dummy).
    """

    dataset_name: str


class QueryModel(RequestModel):
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
class SmartnoiseSQLRequestModel(RequestModel):
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
class SmartnoiseSynthRequestModel(RequestModel):
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
class OpenDPRequestModel(RequestModel):
    """Base input model for an opendp request."""

    opendp_json: str
    fixed_delta: Optional[float] = None


class OpenDPQueryModel(OpenDPRequestModel, QueryModel):
    """Base input model for an opendp query."""


class OpenDPDummyQueryModel(OpenDPRequestModel, DummyQueryModel):
    """Input model for an opendp query on a dummy dataset."""


# DiffPrivLib
# ----------------------------------------------------------------------------
class DiffPrivLibRequestModel(RequestModel):
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


def model_input_to_lib(request: RequestModel) -> DPLibraries:
    """Return the type of DP library given a RequestModel.

    Args:
        request (RequestModel): The user request

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
