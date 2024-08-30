from typing import List

from admin_database.admin_database import AdminDatabase
from constants import DatasetStoreType
from dataset_store.basic_dataset_store import BasicDatasetStore
from dataset_store.dataset_store import DatasetStore
from dataset_store.lru_dataset_store import LRUDatasetStore
from utils.config import DatasetStoreConfig, PrivateDBCredentials
from utils.error_handler import InternalServerException


def dataset_store_factory(
    config: DatasetStoreConfig,
    admin_database: AdminDatabase,
    private_db_credentials: List[PrivateDBCredentials],
) -> DatasetStore:
    """
    Instantiates and returns the correct DatasetStore based on the config.

    Args:
        config (DatasetStoreConfig): A valid DatasetStoreConfig.
        admin_database (AdminDatabase): An initialized AdminDatabase instance.
        private_db_credentials (List[PrivateDBCredentials]):\
             A list of private database credentials.

    Raises:
        InternalServerException: If the dataset store type from the config
            does not exist.

    Returns:
        DatasetStore: The correct DatasetStore instance.
    """
    ds_store_type = config.ds_store_type

    match config.ds_store_type:
        case DatasetStoreType.BASIC:
            return BasicDatasetStore(admin_database, private_db_credentials)
        case DatasetStoreType.LRU:
            return LRUDatasetStore(
                admin_database, private_db_credentials, config.max_memory_usage
            )
        case _:
            raise InternalServerException(
                f"Dataset Store type {ds_store_type} does not exist."
            )
