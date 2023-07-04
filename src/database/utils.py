from utils.constants import CONF_DB_TYPE_MONGODB, CONF_DB_TYPE_YAML
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
        db_port = config.port
        db_name = config.db_name
        db_username = config.username
        db_password = config.password

        # db_url = f"mongodb://{db_addr}:{db_port}/"

        db_url = f'mongodb://{db_username}:{db_password}@mongodb-0.mongodb-headless:{db_port},mongodb-1.mongodb-headless:{db_port}/{db_name}'

        return MongoDB_Database(db_url)

    else:
        raise Exception(f"Database type {db_type} not supported.")
