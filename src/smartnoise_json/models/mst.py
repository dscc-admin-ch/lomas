"""
This is the MWEMSynthesizer synthasizer from OpenDP SmartNoise.
Source: https://github.com/opendp/smartnoise-sdk/tree/main/synth

Copyright: Oblivious Software Ltd, 2022.
"""

from .base import SDModel
from typing import Dict, List

from pydantic import BaseModel, ValidationError, validator
import pandas as pd

# the opendp smartnoise synth data package
from snsynth import Synthesizer
# from snsynth.mst import MSTSynthesizer
import json
import tempfile


class MSTParams(BaseModel):
    # args and defaults from:
    # https://github.com/opendp/smartnoise-sdk/blob/main/synth/snsynth/mwem.py

    delta: float = 1e-9
    

class MST(SDModel):

    def __init__(self, data: pd.DataFrame, epsilon: float, delta: float):
        return super().__init__(data, epsilon, delta)

    def fit(self) -> None:
        # the data to fit is in self._data and is a dataframe
        # the function should have no return, only fit any internals 
        # eg self._model etc as required for sampling

        cols = self.catagorical_mapping
        cols_len = {k: len(v) for k, v in cols.items()}
        print(cols_len, self.catagorical_mapping)
        tfile = tempfile.NamedTemporaryFile(mode="w+")
        json.dump(cols_len, tfile)
        tfile.flush()

        Domains = {
            "data_meta": tfile.name
        }
        
        self._model = Synthesizer.create('mst', epsilon=self.epsilon, delta=self.delta)
        #TODO - Currently MST fails 
        # MSTSynthesizer(domains_dict=Domains, 
        #                    domain='data_meta',
        #                    epsilon=self.epsilon)

        self._model.fit(self.data, preprocessor_eps=1)

    def sample(self, num_samples: int) -> pd.DataFrame:
        # you should use the model etc trained in the self.fit() to 
        # sample `num_samples` samples and return a dataframe.

        samples = self._model.sample(num_samples)

        # use self.to_DataFrame(arr: np.array) to return to original 
        # catagories and column labels.
        return self.to_DataFrame(samples)