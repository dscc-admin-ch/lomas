from admin_database.admin_database import AdminDatabase
from admin_database.mongodb_database import AdminMongoDatabase
from admin_database.yaml_database import AdminYamlDatabase
from constants import AdminDBType
from utils.config import Config, DBConfig
from utils.error_handler import InternalServerException


def database_factory(config: DBConfig) -> AdminDatabase:
    """Instantiates and returns the correct database type described in the
    provided config.

    Args:
        config (DBConfig): _description_

    Raises:
        InternalServerException: _description_

    Returns:
        AdminDatabase: _description_
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
        config (DBConfig): _description_

    Returns:
        str: _description_
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
