from admin_database.admin_database import AdminDatabase
from constants import ConfDatasetStore
from dataset_store.basic_dataset_store import BasicDatasetStore
from dataset_store.dataset_store import DatasetStore
from dataset_store.lru_dataset_store import LRUDatasetStore
from utils.config import DatasetStoreConfig
from utils.error_handler import InternalServerException


def dataset_store_factory(
    config: DatasetStoreConfig, admin_database: AdminDatabase
) -> DatasetStore:
    """
    Instantiates and returns the correct DatasetStore based on the config."""
    ds_store_type = config.ds_store_type

    match config.ds_store_type:
        case ConfDatasetStore.BASIC:
            return BasicDatasetStore(admin_database)
        case ConfDatasetStore.LRU:
            return LRUDatasetStore(admin_database, config.max_memory_usage)
        case _:
            raise InternalServerException(
                f"Dataset Store type {ds_store_type} does not exist."
            )
