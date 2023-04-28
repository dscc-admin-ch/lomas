"""
This is the MWEMSynthesizer synthasizer from OpenDP SmartNoise.
Source: https://github.com/opendp/smartnoise-sdk/tree/main/synth

Copyright: Oblivious Software Ltd, 2022.
"""

from .base import SDModel
from typing import Dict, List

from pydantic import BaseModel
import pandas as pd

# the opendp smartnoise synth data package
import snsynth


class MWEMParams(BaseModel):
    # args and defaults from:
    # https://github.com/opendp/smartnoise-sdk/blob/main/synth/snsynth/mwem.py

    q_count: int = 400
    iterations: int = 30
    mult_weights_iterations: int = 20
    splits: List = []
    split_factor: int = None
    max_bin_count: int = 500
    custom_bin_count: Dict = {}
    max_retries_exp_mechanism: int = 1000


class MWEM(SDModel):
    def __init__(
        self,
        data: pd.DataFrame,
        epsilon: float,
        delta: float,
        select_cols: List[str] = [],
        mul_matrix=None,
    ):
        return super().__init__(
            data,
            epsilon,
            delta,
            select_cols,
            mul_matrix,
        )

    def fit(self) -> None:
        # the data to fit is in self.data and is a dataframe
        # the function should have no return, only fit any internals
        # eg self._model etc as required for sampling

        self._model = snsynth.Synthesizer.create(
            "mwem",
            epsilon=self.epsilon,
        )
        self._model.fit(
            self.data,
            preprocessor_eps=2,
        )

    def sample(self, num_samples: int) -> pd.DataFrame:
        # you should use the model etc trained in the self.fit() to
        # sample `num_samples` samples and return a dataframe.

        samples = self._model.sample(num_samples)

        # use self.to_DataFrame(arr: np.array) to return to original
        # catagories and column labels.
        return self.to_DataFrame(samples)
