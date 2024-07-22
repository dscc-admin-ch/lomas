from constants import DPLibraries
from dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from dp_queries.dp_libraries.opendp import OpenDPQuerier
from dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from dp_queries.dp_libraries.smartnoise_synth import SmartnoiseSynthQuerier
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.error_handler import InternalServerException


def querier_factory(lib: str, private_dataset: PrivateDataset) -> DPQuerier:
    """Builds the correct DPQuerier instance.

    Args:
        lib (str): The library to build the querier for.
            One of :py:class:`DPLibraries`.
        private_dataset (PrivateDataset): The dataset to query.

    Raises:
        InternalServerException: If the library is unknown.

    Returns:
        DPQuerier: The built DPQuerier.
    """
    match lib:
        case DPLibraries.SMARTNOISE_SQL:
            querier = SmartnoiseSQLQuerier(private_dataset)

        case DPLibraries.SMARTNOISE_SYNTH:
            querier = SmartnoiseSynthQuerier(private_dataset)

        case DPLibraries.OPENDP:
            querier = OpenDPQuerier(private_dataset)

        case DPLibraries.DIFFPRIVLIB:
            querier = DiffPrivLibQuerier(private_dataset)

        case _:
            raise InternalServerException(f"Unknown library: {lib}")
    return querier
