from typing import List

from snsynth.transform.table import TableTransformer

from utils.collections_models import Metadata


def data_transforms(metadata: Metadata, select_cols: List) -> TableTransformer:
    # TODO TableTransformer based on metadata to ensure preprocessor_eps=0.0
    # synth = Synthesizer.create('dpctgan', epsilon=1.0, verbose=True)
    # sample = synth.fit_sample(pums, transformer=tt, preprocessor_eps=0.0)
    # assert (synth.odometer.spent == (0.0, 0.0))
    return TableTransformer()


def get_columns_by_types(
    metadata: Metadata, select_cols: List
) -> List[List[str]]:
    # https://docs.smartnoise.org/synth/index.html#preprocessor-hints
    # TODO categorical and continuous columns based on metadata
    # https://docs.smartnoise.org/synth/index.html#data-transforms
    categorical_columns = []
    ordinal_columns = []
    continuous_columns = []
    return categorical_columns, ordinal_columns, continuous_columns
