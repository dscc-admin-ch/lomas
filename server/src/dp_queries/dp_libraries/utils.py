from constants import DPLibraries
from dp_queries.dp_libraries.open_dp import OpenDPQuerier
from dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from utils.error_handler import InternalServerException


def querier_factory(lib, private_dataset):
    match lib:
        case DPLibraries.SMARTNOISE_SQL:
            querier = SmartnoiseSQLQuerier(private_dataset)

        case DPLibraries.OPENDP:
            querier = OpenDPQuerier(private_dataset)

        case _:
            raise InternalServerException(f"Unknown library: {lib}")
    return querier
