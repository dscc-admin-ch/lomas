from aio_pika.patterns.rpc import Proxy
from csvw_eo.make_dummy_from_metadata import make_dummy_from_metadata

from lomas_core.models.requests import DummyQueryModel
from lomas_server.data_connector.in_memory_connector import InMemoryConnector


def get_dummy_dataset_for_query(admin_database: Proxy, query_json: DummyQueryModel) -> InMemoryConnector:
    """Get a dummy dataset for a given query.

    Args:
        admin_database (Proxy): A Proxy for an initialized instance of an AdminDatabase.
        query_json (RequestModel): The request object for the query.

    Returns:
        InMemoryConnector: An in memory dummy dataset instance.
    """
    # Create dummy dataset based on seed and number of rows
    metadata = admin_database.get_dataset_metadata(dataset_name=query_json.dataset_name)
    df = make_dummy_from_metadata(
        metadata.to_dict(),
        query_json.dummy_nb_rows,
        query_json.dummy_seed,
    )
    return InMemoryConnector(metadata=metadata, df=df)
