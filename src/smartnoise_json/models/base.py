# This is just a template for the synthetic data class
from abc import ABC, abstractmethod
from typing import List, Set, Dict, Tuple, Optional, Literal

import pandas as pd
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import pandas as pd
import numpy as np

import io


class SDModel(ABC):

    def __init__(self, data: pd.DataFrame, epsilon: float):
        #self.params = params
        self.epsilon = epsilon
        #self.data = data

        # create a column mapping from catagorical to ints [1,2,3,4....]
        col_mapping = {}
        for cat in data.columns:
            if cat != "id":
                col_mapping[cat] = dict([
                    (category, code) for code, category in enumerate(data[cat].astype('category').cat.categories)
                    ])

                data[cat] = data[cat].map(lambda x: col_mapping[cat][x])

        self.catagorical_mapping = col_mapping

        self.data = data

        self.fit()

    @abstractmethod  # Decorator to define an abstract method
    def fit(self) -> None:
        # the data to fit is in self.data and is a dataframe
        # the function should have no return, only fit any internals eg self._model etc as required for sampling
        pass

    @abstractmethod  # Decorator to define an abstract method
    def sample(self, num_samples: int) -> pd.DataFrame:
        # you should use the model etc trained in the self.fit() to sample `num_samples` samples and return a dataframe
        pass

    def to_DataFrame(self, arr: np.array) -> pd.DataFrame:
        samples_df = pd.DataFrame(arr, columns=self.data.columns)

        for col in samples_df.columns:
            inv_map = [k for k, v in self.catagorical_mapping[col].items()]

            samples_df[col] = samples_df[col].map(lambda x: inv_map[x])

        return samples_df


    def export(self, num_samples: int = 10000) -> StreamingResponse:
        
        stream = io.StringIO()

        # CSV creation
        self.sample(num_samples).to_csv(stream, index = False)
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=synthetic_data.csv"

        return response
        