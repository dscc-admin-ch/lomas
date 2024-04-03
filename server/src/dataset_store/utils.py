from constants import (
    CONF_DATASET_STORE_TYPE_BASIC,
    CONF_DATASET_STORE_TYPE_LRU,
)
from dataset_store.dataset_store import DatasetStore
from dataset_store.basic_dataset_store import BasicDatasetStore
from dataset_store.lru_dataset_store import LRUDatasetStore
from utils.config import DatasetStoreConfig
from admin_database.admin_database import AdminDatabase


def dataset_store_factory(
    config: DatasetStoreConfig, admin_database: AdminDatabase
) -> DatasetStore:
    """
    Instantiates and returns the correct DatasetStore based on the config."""
    ds_store_type = config.ds_store_type

    if ds_store_type == CONF_DATASET_STORE_TYPE_BASIC:
        return BasicDatasetStore(admin_database)
    elif ds_store_type == CONF_DATASET_STORE_TYPE_LRU:
        return LRUDatasetStore(admin_database, config.max_memory_usage)
    else:
        raise ValueError(f"Dataset Store type {ds_store_type} does not exist.")
