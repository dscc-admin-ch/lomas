"""
This is the DP-CTGAN synthasizer from OpenDP SmartNoise.
Source: https://github.com/opendp/smartnoise-sdk/tree/main/synth

Copyright: Oblivious Software Ltd, 2022.
"""

from .base import SDModel
from typing import List

import pandas as pd

# the opendp smartnoise synth data package
from snsynth import (
    Synthesizer,
)

# from snsynth.pytorch.nn import PATECTGAN as snsynth_PATECTGAN
# from snsynth.pytorch import PytorchDPSynthesizer
# from snsynth.preprocessors.data_transformer import BaseTransformer


class PATECTGAN(SDModel):
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
        # the data to fit is in self._data and is a dataframe
        # the function should have no return, only fit any internals
        # eg self._model etc as required for sampling

        self._model = Synthesizer.create(
            "patectgan",
            epsilon=self.epsilon,
            delta=self.delta,
        )
        self._model.fit(
            self.data,
            preprocessor_eps=2.0,
        )
        # self._model = PytorchDPSynthesizer(
        #     self.epsilon, snsynth_PATECTGAN(), None
        # )
        # #TODO BaseTransformer no longer exists, need to update
        # self._model.fit(
        #     self.data,
        #     categorical_columns=list(self.data.columns),
        #     transformer=BaseTransformer
        #     )

    def sample(self, num_samples: int) -> pd.DataFrame:
        # you should use the model etc trained in the self.fit() to
        # sample `num_samples` samples and return a dataframe.

        samples = self._model.sample(num_samples)

        # use self.to_DataFrame(arr: np.array) to return to original
        # catagories and column labels.
        return self.to_DataFrame(samples)
