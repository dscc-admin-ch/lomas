import pandas as pd
from snsynth import Synthesizer

from constants import DEFAULT_NB_SYNTHETIC_SAMPLES, DPLibraries
from dp_queries.dp_libraries.smartnoise_synth_utils import (
    data_transforms,
    get_columns_by_types,
)
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
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
        # Preprocessing from metadata
        metadata = self.private_dataset.get_metadata()
        transformer = data_transforms(metadata)
        (
            categorical_columns,
            ordinal_columns,
            continuous_columns,
        ) = get_columns_by_types(metadata)

        # Create synthesizer
        synth = Synthesizer.create(
            query_json.model, epsilon=query_json.epsilon
        )

        try:
            synth = synth.fit(
                data=self.private_dataset.get_pandas_df(),
                transformer=transformer,
                categorical_columns=categorical_columns,
                ordinal_columns=ordinal_columns,
                continuous_columns=continuous_columns,
                preprocessor_eps=0.0,
                nullable=query_json.nullable,
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model:" + str(e)
            ) from e

        if query_json.nb_samples is not None:
            nb_samples = query_json.nb_samples
        elif metadata.rows is not None:
            nb_samples = metadata.rows
        else:
            nb_samples = DEFAULT_NB_SYNTHETIC_SAMPLES

        if query_json.condition is not None:
            synth_df = synth.sample_conditional(
                nb_samples, query_json.condition
            )
        else:
            synth_df = synth.sample(nb_samples)
        return synth_df
