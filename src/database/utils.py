from utils.constants import CONF_DB_TYPE_MONGODB, CONF_DB_TYPE_YAML, DATABASE_NAME, MONGODB_PORT
from database.database import Database
from database.mongodb_database import MongoDB_Database
from database.yaml_database import YamlDatabase
from utils.config import DBConfig


def database_factory(config: DBConfig) -> Database:
    """
    Instantiates and returns the correct database type described in the
    provided config.
    """
    db_type = config.db_type

    if db_type == CONF_DB_TYPE_YAML:
        yaml_database_file = config.db_file

        return YamlDatabase(yaml_database_file)

    elif db_type == CONF_DB_TYPE_MONGODB:
        # db_addr = config.address
        # db_url = f"mongodb://{db_addr}:{db_port}/"

        import os
        # Get environment variables
        db_username = os.getenv('MONGO_USERNAME')
        db_password = os.environ.get('MONGO_PWD')

        db_url = f'mongodb://{db_username}:{db_password}@mongodb-0.mongodb-headless:{MONGODB_PORT},mongodb-1.mongodb-headless:{MONGODB_PORT}/{DATABASE_NAME}'

        return MongoDB_Database(db_url)

    else:
        raise Exception(f"Database type {db_type} not supported.")
