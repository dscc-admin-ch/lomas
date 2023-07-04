import os
import hvac

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


def get_credentials():
    # Connect to the vault
    client = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ['VAULT_TOKEN'])
    mongodb_secret = client.secrets.kv.v2.read_secret_version(
        mount_point=os.environ["VAULT_MOUNT"], path=f"{os.environ["VAULT_TOP_DIR"]}/{VAULT_NAME}"
    )

    # Get environment variables
    db_username = mongodb_secret["data"]["data"]["MONGO_USERNAME"]
    db_password = mongodb_secret["data"]["data"]["MONGO_PASSWORD"]

    return db_username, db_password
