from types import SimpleNamespace

from pymongo import MongoClient
from pymongo.database import Database

from utils.config import DBConfig, get_config


def get_mongodb_url(config: DBConfig) -> str:
    """Get URL of the administration MongoDB.

    Args:
        config (DBConfig): An instance of DBConfig.

    Returns:
        str: A correctly formatted url for connecting to the
            MongoDB database.
    """
    db_username = config.username
    db_password = config.password
    db_address = config.address
    db_port = config.port
    db_name = config.db_name

    db_url = (
        f"mongodb://{db_username}:{db_password}@{db_address}:"
        f"{db_port}/{db_name}?authSource=defaultdb"
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
    db_args = SimpleNamespace(**vars(get_config().admin_database))
    db_url = get_mongodb_url(db_args)
    return MongoClient(db_url)[db_args.db_name]
