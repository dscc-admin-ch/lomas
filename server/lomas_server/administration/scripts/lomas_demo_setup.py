from typing import Optional

from mongomock import Database, MongoClient
from pydantic_settings import BaseSettings, SettingsConfigDict

from lomas_core.logger import LOG
from lomas_core.models.config import MongoDBConfig
from lomas_core.models.constants import AdminDBType
from lomas_server.admin_database.utils import get_mongodb_url
from lomas_server.administration.keycloak_admin import KeycloakAccessConfig, add_kc_users_via_yaml
from lomas_server.administration.mongodb_admin import (
    add_datasets_via_yaml,
    add_users_via_yaml,
    drop_collection,
)


def add_demo_data_to_mongodb(
    mongo_db: Database,
    user_yaml: str = "/data/collections/user_collection.yaml",
    dataset_yaml: str = "/data/collections/dataset_collection.yaml",
) -> None:
    """
    Adds the demo data to the mongodb admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service.

    Args:
        user_yaml (str): path to user collection yaml file
        dataset_yaml (str): path to dataset collection yaml file
    """
    LOG.info("Creating user collection")
    add_users_via_yaml(
        mongo_db,
        clean=True,
        overwrite=True,
        yaml_file=user_yaml,
    )

    LOG.info("Creating datasets and metadata collection")
    add_datasets_via_yaml(
        mongo_db,
        clean=True,
        overwrite_datasets=True,
        overwrite_metadata=True,
        yaml_file=dataset_yaml,
    )

    LOG.info("Empty archives")
    drop_collection(mongo_db, collection="queries_archives")


class DemoAdminConfig(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_demo_setup_",
        env_file="lomas_demo_setup.env",
        case_sensitive=False,
    )

    kc_skip: bool
    kc_address: Optional[str]
    kc_port: Optional[int]
    kc_realm: Optional[str]
    kc_client_id: Optional[str]
    kc_client_secret: Optional[str]
    kc_use_tls: Optional[bool]

    mg_address: str
    mg_port: int
    mg_username: str
    mg_password: str
    mg_db_name: str

    user_yaml: str
    dataset_yaml: str


if __name__ == "__main__":
    demo_config = DemoAdminConfig()

    mongodb_config = MongoDBConfig(
        db_type=AdminDBType.MONGODB,
        address=demo_config.mg_address,
        port=demo_config.mg_port,
        username=demo_config.mg_username,
        password=demo_config.mg_password,
        db_name=demo_config.mg_db_name,
        max_pool_size=100,
        min_pool_size=0,
        max_connecting=2,
    )

    mg_db_url = get_mongodb_url(mongodb_config)
    mongo_db: Database = MongoClient(mg_db_url)[demo_config.mg_db_name]

    add_demo_data_to_mongodb(mongo_db, demo_config.user_yaml, demo_config.dataset_yaml)

    kc_config = KeycloakAccessConfig(**vars(demo_config))

    add_kc_users_via_yaml(kc_config, demo_config.user_yaml, clean=True, overwrite=True)
