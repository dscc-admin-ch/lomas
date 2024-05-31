from types import SimpleNamespace

from pymongo import MongoClient
from pymongo.database import Database

from admin_database.admin_database import AdminDatabase
from admin_database.mongodb_database import AdminMongoDatabase
from admin_database.yaml_database import AdminYamlDatabase
from constants import AdminDBType
from utils.config import DBConfig, get_config
from utils.error_handler import InternalServerException


def database_factory(config: DBConfig) -> AdminDatabase:
    """Instantiates and returns the correct database type described in the
    provided config.

    Args:
        config (DBConfig): An instance of DBconfig.

    Raises:
        InternalServerException: If the specified database type
        is not supported.

    Returns:
        AdminDatabase: A instance of the correct type of AdminDatabase.
    """
    db_type = config.db_type

    match db_type:
        case AdminDBType.MONGODB_TYPE:
            db_url = get_mongodb_url(config)
            db_name = config.db_name
            return AdminMongoDatabase(db_url, db_name)

        case AdminDBType.YAML_TYPE:
            yaml_database_file = config.db_file
            return AdminYamlDatabase(yaml_database_file)

        case _:
            raise InternalServerException(
                f"Database type {db_type} not supported."
            )


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
