from admin_database.admin_database import AdminDatabase
from admin_database.mongodb_database import AdminMongoDatabase
from constants import CONF_DB_TYPE_MONGODB
from utils.config import Config, DBConfig
from utils.error_handler import InternalServerException


def database_factory(config: DBConfig) -> AdminDatabase:
    """
    Instantiates and returns the correct database type described in the
    provided config.
    """
    db_type = config.db_type

    if db_type == CONF_DB_TYPE_MONGODB:
        db_url = get_mongodb_url(config)
        db_name = config.db_name

        return AdminMongoDatabase(db_url, db_name)
    else:
        raise InternalServerException(
            f"Database type {db_type} not supported."
        )


def get_mongodb_url(config: Config) -> str:
    """
    Get URL of the administration MongoDB.
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
