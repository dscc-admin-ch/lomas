from constants import LIB_DIFFPRIVLIB, LIB_OPENDP, LIB_SMARTNOISE_SQL
from dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from dp_queries.dp_libraries.open_dp import OpenDPQuerier
from dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier


def querier_factory(lib, private_dataset):
    if lib == LIB_SMARTNOISE_SQL:
        querier = SmartnoiseSQLQuerier(private_dataset)

    elif lib == LIB_OPENDP:
        querier = OpenDPQuerier(private_dataset)

    elif lib == LIB_DIFFPRIVLIB:
        querier = DiffPrivLibQuerier(private_dataset)

    else:
        raise Exception(
            f"Trying to create a querier for library {lib}. "
            "This should never happen."
        )
    return querier
