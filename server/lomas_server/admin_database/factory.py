from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.admin_database.mongodb_database import AdminMongoDatabase
from lomas_server.admin_database.utils import get_mongodb_url
from lomas_server.admin_database.yaml_database import AdminYamlDatabase
from lomas_server.constants import AdminDBType
from lomas_server.utils.config import DBConfig
from lomas_server.utils.error_handler import InternalServerException


def admin_database_factory(config: DBConfig) -> AdminDatabase:
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
        case AdminDBType.MONGODB:
            db_url = get_mongodb_url(config)
            db_name = config.db_name
            return AdminMongoDatabase(db_url, db_name)

        case AdminDBType.YAML:
            yaml_database_file = config.db_file
            return AdminYamlDatabase(yaml_database_file)

        case _:
            raise InternalServerException(
                f"Database type {db_type} not supported."
            )
