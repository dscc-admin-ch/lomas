import os

from utils.constants import (
    CONF_DB_TYPE_MONGODB,
    CONF_DB_TYPE_YAML,
)
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
        db_url = get_mongodb_url(config)
        db_name = config.db_name

        return MongoDB_Database(db_url, db_name)

    else:
        raise Exception(f"Database type {db_type} not supported.")


def get_mongodb_url(config):
    # I would advocate that our application soes not become "vault aware".
    # I am guessing making it as such could potentially hinder its
    # adoption.

    # Connect to the vault
    #client = hvac.Client(
    #    url=os.environ["VAULT_ADDR"],
    #    token=os.environ['VAULT_TOKEN']
    #)
    #mongodb_secret = client.secrets.kv.v2.read_secret_version(
    #    mount_point=os.environ["VAULT_MOUNT"],
    #    path=f'{os.environ["VAULT_TOP_DIR"]}/{VAULT_NAME}'
    #)

    # Get environment variables
    #db_username = mongodb_secret["data"]["data"]["MONGO_USERNAME"]
    #db_password = mongodb_secret["data"]["data"]["MONGO_PASSWORD"]

    db_username = config.username
    db_password = config.password
    db_address = config.address
    db_port = config.port
    db_name = config.db_name

    # TODO check this...
    db_url = f'mongodb://{db_username}:{db_password}@{db_address}:{db_port}/{db_name}?authSource=defaultdb'
    #client = MongoClient('mongodb://user_pwd:pwd@mongodb-0.mongodb-headless:0/defaultdb?authSourcedefaultdb')
    
    #db_url = f'mongodb://{db_username}:{db_password}@mongodb-0.mongodb-headless:{MONGODB_PORT},mongodb-1.mongodb-headless:{MONGODB_PORT}/{DATABASE_NAME}'

    return db_url
