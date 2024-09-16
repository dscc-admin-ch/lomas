from lomas_core.constants import DPLibraries
from lomas_core.error_handler import InternalServerException

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from lomas_server.dp_queries.dp_libraries.opendp import OpenDPQuerier
from lomas_server.dp_queries.dp_libraries.smartnoise_sql import (
    SmartnoiseSQLQuerier,
)
from lomas_server.dp_queries.dp_libraries.smartnoise_synth import (
    SmartnoiseSynthQuerier,
)
from lomas_server.dp_queries.dp_querier import DPQuerier


def querier_factory(
    lib: str,
    data_connector: DataConnector,
    admin_database: AdminDatabase,
) -> DPQuerier:
    """Builds the correct DPQuerier instance.

    Args:
        lib (str): The library to build the querier for.
            One of :py:class:`DPLibraries`.
        data_connector (DataConnector): The dataset to query.
        admin_database (AdminDatabase): An initialized instance of
                an AdminDatabase.

    Raises:
        InternalServerException: If the library is unknown.

    Returns:
        DPQuerier: The built DPQuerier.
    """
    querier: DPQuerier
    match lib:
        case DPLibraries.SMARTNOISE_SQL:
            querier = SmartnoiseSQLQuerier(data_connector, admin_database)

        case DPLibraries.SMARTNOISE_SYNTH:
            querier = SmartnoiseSynthQuerier(data_connector, admin_database)

        case DPLibraries.OPENDP:
            querier = OpenDPQuerier(data_connector, admin_database)

        case DPLibraries.DIFFPRIVLIB:
            querier = DiffPrivLibQuerier(data_connector, admin_database)

        case _:
            raise InternalServerException(f"Unknown library: {lib}")
    return querier
