from typing import List, Optional

from lomas_core.models.requests import (
    SmartnoiseSynthDummyQueryModel,
    SmartnoiseSynthQueryModel,
    SmartnoiseSynthRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse
from smartnoise_synth_logger import serialise_constraints

from lomas_client.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    SMARTNOISE_SYNTH_READ_TIMEOUT,
    SNSYNTH_DEFAULT_SAMPLES_NB,
)
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import (
    validate_model_response,
    validate_synthesizer,
)


class SmartnoiseSynthClient:
    """A client for executing and estimating the cost of SmartNoiseSynth queries."""

    def __init__(self, http_client: LomasHttpClient):
        self.http_client = http_client

    def cost(
        self,
        synth_name: str,
        epsilon: float,
        delta: Optional[float] = None,
        select_cols: List[str] = [],
        synth_params: dict = {},
        nullable: bool = True,
        constraints: dict = {},
    ) -> Optional[CostResponse]:
        """This function estimates the cost of executing a SmartNoise query.
        Args:
            synth_name (str): name of the Synthesizer model to use.
                Available synthesizer are
                    - "aim",
                    - "mwem",
                    - "dpctgan" with `disabled_dp` always forced to False and a
                    warning due to not cryptographically secure random generator
                    - "patectgan"
                    - "dpgan" with a warning due to not cryptographically secure
                    random generator
                Available under certain conditions:
                    - "mst" if `return_model=False`
                    - "pategan" if the dataset has enough rows
                Not available:
                    - "pacsynth" due to Rust panic error
                    - "quail" currently unavailable in Smartnoise Synth
                For further documentation on models, please see here:
                https://docs.smartnoise.org/synth/index.html#synthesizers-reference
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
            select_cols (List[str]): List of columns to select.
                Defaults to None.
            synth_params (dict): Keyword arguments to pass to the synthesizer
                constructor.
                See https://docs.smartnoise.org/synth/synthesizers/index.html#, provide
                all parameters of the model except `epsilon` and `delta`.
                Defaults to None.
            nullable (bool): True if some data cells may be null
                Defaults to True.
            constraints (dict): Dictionnary for custom table transformer constraints.
                Column that are not specified will be inferred based on metadata.
                Defaults to {}.
                For further documentation on constraints, please see here:
                https://docs.smartnoise.org/synth/transforms/index.html.
                Note: lambda function in `AnonimizationTransformer` are not supported.
        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        validate_synthesizer(synth_name)
        constraints = serialise_constraints(constraints) if constraints else ""

        body_dict = {
            "dataset_name": self.http_client.dataset_name,
            "synth_name": synth_name,
            "epsilon": epsilon,
            "delta": delta,
            "select_cols": select_cols,
            "synth_params": synth_params,
            "nullable": nullable,
            "constraints": constraints,
        }
        body = SmartnoiseSynthRequestModel.model_validate(body_dict)
        res = self.http_client.post(
            "estimate_smartnoise_synth_cost", body, SMARTNOISE_SYNTH_READ_TIMEOUT
        )

        return validate_model_response(res, CostResponse)

    def query(
        self,
        synth_name: str,
        epsilon: float,
        delta: Optional[float] = None,
        select_cols: List[str] = [],
        synth_params: dict = {},
        nullable: bool = True,
        constraints: dict = {},
        dummy: bool = False,
        return_model: bool = False,
        condition: str = "",
        nb_samples: int = SNSYNTH_DEFAULT_SAMPLES_NB,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[QueryResponse]:
        """This function executes a SmartNoise Synthetic query.
        Args:
            synth_name (str): name of the Synthesizer model to use.
                Available synthesizer are
                    - "aim",
                    - "mwem",
                    - "dpctgan" with `disabled_dp` always forced to False and a
                    warning due to not cryptographically secure random generator
                    - "patectgan"
                    - "dpgan" with a warning due to not cryptographically secure
                    random generator
                Available under certain conditions:
                    - "mst" if `return_model=False`
                    - "pategan" if the dataset has enough rows
                Not available:
                    - "pacsynth" due to Rust panic error
                    - "quail" currently unavailable in Smartnoise Synth
                For further documentation on models, please see here:
                https://docs.smartnoise.org/synth/index.html#synthesizers-reference
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
            select_cols (List[str]): List of columns to select.
                Defaults to None.
            synth_params (dict): Keyword arguments to pass to the synthesizer
                constructor.
                See https://docs.smartnoise.org/synth/synthesizers/index.html#, provide
                all parameters of the model except `epsilon` and `delta`.
                Defaults to None.
            nullable (bool): True if some data cells may be null
                Defaults to True.
            constraints: Dictionnary for custom table transformer constraints.
                Column that are not specified will be inferred based on metadata.
                Defaults to {}.
                For further documentation on constraints, please see here:
                https://docs.smartnoise.org/synth/transforms/index.html.
                Note: lambda function in `AnonimizationTransformer` are not supported.
            return_model (bool): True to get Synthesizer model, False to get samples
                Defaults to False
            condition (Optional[str]): sampling condition in `model.sample`
                (only relevant if return_model is False)
                Defaults to "".
            nb_samples (Optional[int]): number of samples to generate.
                (only relevant if return_model is False)
                Defaults to SNSYNTH_DEFAULT_SAMPLES_NB
            dummy (bool, optional): Whether to use a dummy dataset.
                Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.
                Defaults to DUMMY_SEED.
        Returns:
            Optional[dict]: A Pandas DataFrame containing the query results.
        """
        validate_synthesizer(synth_name, return_model)
        constraints = serialise_constraints(constraints) if constraints else ""

        body_dict = {
            "dataset_name": self.http_client.dataset_name,
            "synth_name": synth_name,
            "epsilon": epsilon,
            "delta": delta,
            "select_cols": select_cols,
            "synth_params": synth_params,
            "nullable": nullable,
            "constraints": constraints,
            "return_model": return_model,
            "condition": condition,
            "nb_samples": nb_samples,
        }
        if dummy:
            endpoint = "dummy_smartnoise_synth_query"
            body_dict["dummy_nb_rows"] = nb_rows
            body_dict["dummy_seed"] = seed
            request_model = SmartnoiseSynthDummyQueryModel
        else:
            endpoint = "smartnoise_synth_query"
            request_model = SmartnoiseSynthQueryModel

        body = request_model.model_validate(body_dict)
        res = self.http_client.post(endpoint, body, SMARTNOISE_SYNTH_READ_TIMEOUT)

        return validate_model_response(res, QueryResponse)
