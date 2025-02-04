import logging

from pymongo import MongoClient
from pymongo.database import Database

from lomas_core.error_handler import InternalServerException
from lomas_core.models.config import MongoDBConfig
from lomas_server.utils.config import get_config


def get_mongodb_url(config: MongoDBConfig) -> str:
    """Get URL of the administration MongoDB.

    Args:
        config (MongoDBConfig): An instance of DBConfig.

    Returns:
        str: A correctly formatted url for connecting to the
            MongoDB database.
    """
    db_username = config.username
    db_password = config.password
    db_address = config.address
    db_port = config.port
    db_name = config.db_name
    db_max_pool_size = config.max_pool_size
    db_min_pool_size = config.min_pool_size
    db_max_connecting = config.max_connecting

    db_url = (
        f"mongodb://{db_username}:{db_password}@{db_address}:"
        f"{db_port}/{db_name}?authSource=defaultdb"
        f"&maxPoolSize={db_max_pool_size}&minPoolSize={db_min_pool_size}"
        f"&maxConnecting={db_max_connecting}"
    )

    return db_url


def get_mongodb() -> Database:
    """Get URL of the administration MongoDB.

    Args:
        config (DBConfig): An instance of DBConfig.

    Returns:
        str: A correctly formatted url for connecting to the
            MongoDB database.
    """
    admin_config = get_config().admin_database
    if isinstance(admin_config, MongoDBConfig):
        db_url = get_mongodb_url(admin_config)
    else:
        raise InternalServerException("Expected MongoDBConfig, found {type(admin_config)}.")

    return MongoClient(db_url)[admin_config.db_name]
