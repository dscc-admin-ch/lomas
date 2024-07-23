from typing import List

import numpy as np
import pandas as pd
from snsynth import Synthesizer

from constants import DEFAULT_NB_SYNTHETIC_SAMPLES, DPLibraries
from dp_queries.dp_libraries.smartnoise_synth_utils import (
    data_transforms,
    get_columns_by_types,
)
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.collections_models import Metadata
from utils.error_handler import ExternalLibraryException, InvalidQueryException
from utils.input_models import SmartnoiseSynthModel, SmartnoiseSynthModelCost


class SmartnoiseSynthQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the SmartNoiseSynth library.
    """

    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        """Initializer.

        Args:
            private_dataset (PrivateDataset): Private dataset to query.
        """
        super().__init__(private_dataset)

    def cost(
        self, query_json: SmartnoiseSynthModelCost
    ) -> tuple[float, float]:
        """Return cost of query

        Args:
            query_json (SmartnoiseSynthModelCost): JSON request object for the query.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        # synth.odometer.spent
        return query_json.epsilon, query_json.delta

    def _preprocess_metadata(self, metadata: Metadata, select_cols: List[str]):
        self.transformer = data_transforms(metadata, select_cols)
        (
            self.categorical_columns,
            self.ordinal_columns,
            self.continuous_columns,
        ) = get_columns_by_types(metadata, select_cols)
        self.public_nb_row = metadata.nb_row

    def _preprocess_data(self, select_cols: List[str], mul_matrix: np.array):
        if select_cols:
            try:
                self.private_data = self.private_data[select_cols]
            except Exception as e:
                raise InvalidQueryException(
                    "Error while selecting provided select_cols: " + str(e)
                )

        if mul_matrix:
            try:
                np_matrix = np.array(mul_matrix)
                dt = self.private_data.to_numpy().dot(np_matrix.T)
                self.private_data = pd.DataFrame(dt)
            except Exception as e:
                raise InvalidQueryException(
                    f"Failed to multiply provided mul_matrix: {(str(e))}"
                )

    def _fit(self, nullable: bool):
        try:
            self.model = self.model.fit(
                data=self.private_data,
                transformer=self.transformer,
                categorical_columns=self.categorical_columns,
                ordinal_columns=self.ordinal_columns,
                continuous_columns=self.continuous_columns,
                preprocessor_eps=0.0,
                nullable=nullable,
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model:" + str(e)
            ) from e

    def _sample(self, nb_samples: int, condition: str, mul_matrix: np.array):
        # Number of samples
        if nb_samples is None:
            nb_samples = (
                self.public_nb_row
                if self.public_nb_row
                else DEFAULT_NB_SYNTHETIC_SAMPLES
            )

        # Sample based on condition
        if condition is not None:
            samples = self.model.sample_conditional(nb_samples, condition)
        else:
            samples = self.model.sample(nb_samples)

        # Format back
        if mul_matrix:
            self.samples_df = pd.DataFrame(samples)
        else:
            self.samples_df = pd.DataFrame(
                samples, columns=self.private_data.columns
            )

    def query(self, query_json: SmartnoiseSynthModel) -> dict:
        """Perform the query and return the response.

        Args:
            query_json (SmartnoiseSynthModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InvalidQueryException: If the budget values are too small to
                perform the query.

        Returns:
            dict: The dictionary encoding of the resulting pd.DataFrame.
        """
        # Preprocessing information from metadata
        metadata = self.private_dataset.get_metadata()
        self._preprocess_metadata(metadata, query_json.select_cols)

        # Prepare data
        self.private_data = self.private_dataset.get_pandas_df()
        self._preprocess_data(query_json.select_cols, query_json.mul_matrix)

        # Create and fit synthesizer
        self.model = Synthesizer.create(
            query_json.model,
            epsilon=query_json.epsilon,
            delta=query_json.delta,
        )
        self._fit(query_json.nullable)

        # Sample from synthesizer
        self._sample(
            query_json.nb_samples, query_json.condition, query_json.mul_matrix
        )

        return self.samples_df
