from lomas_core.error_handler import InternalServerException
from lomas_core.models.config import DBConfig, MongoDBConfig, YamlDBConfig

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.admin_database.mongodb_database import AdminMongoDatabase
from lomas_server.admin_database.utils import get_mongodb_url
from lomas_server.admin_database.yaml_database import AdminYamlDatabase


def admin_database_factory(config: DBConfig) -> AdminDatabase:
    """Instantiates and returns database type described in config.

    Args:
        config (DBConfig): An instance of DBconfig.

    Raises:
        InternalServerException: If the specified database type
        is not supported.

    Returns:
        AdminDatabase: A instance of the correct type of AdminDatabase.
    """

    match config:
        case MongoDBConfig():
            db_url = get_mongodb_url(config)
            db_name = config.db_name
            return AdminMongoDatabase(db_url, db_name)

        case YamlDBConfig():
            yaml_database_file = config.db_file
            return AdminYamlDatabase(yaml_database_file)
        case _:
            raise InternalServerException("Database type not supported.")
