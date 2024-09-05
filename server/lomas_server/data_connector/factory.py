from typing import List

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import PrivateDatabaseType
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.data_connector.path_connector import PathConnector
from lomas_server.data_connector.s3_connector import S3Connector
from lomas_server.utils.config import PrivateDBCredentials, S3CredentialsConfig
from lomas_server.utils.error_handler import InternalServerException


def data_connector_factory(
    dataset_name: str,
    admin_database: AdminDatabase,
    private_db_credentials: List[PrivateDBCredentials],
) -> DataConnector:
    """
    Returns the appropriate dataset class based on dataset storage location

    Args:
        dataset_name (str): The dataset name.
        admin_database (AdminDatabase): An initialized instance
            of AdminDatabase.

    Raises:
        InternalServerException: If the dataset type does not exist.

    Returns:
        DataConnector: The DataConnector instance for this dataset.
    """
    database_type = admin_database.get_dataset_field(
        dataset_name, "database_type"
    )

    ds_metadata = admin_database.get_dataset_metadata(dataset_name)

    match database_type:
        case PrivateDatabaseType.PATH:
            dataset_path = admin_database.get_dataset_field(
                dataset_name, "dataset_path"
            )
            private_db = PathConnector(ds_metadata, dataset_path)
        case PrivateDatabaseType.S3:

            credentials_name = admin_database.get_dataset_field(
                dataset_name, "credentials_name"
            )

            credentials = get_dataset_credentials(
                private_db_credentials, database_type, credentials_name
            )

            credentials.endpoint_url = admin_database.get_dataset_field(
                dataset_name, "endpoint_url"
            )
            credentials.bucket = admin_database.get_dataset_field(
                dataset_name, "bucket"
            )
            credentials.key = admin_database.get_dataset_field(
                dataset_name, "key"
            )

            private_db = S3Connector(ds_metadata, credentials)
        case _:
            raise InternalServerException(
                f"Unknown database type: {database_type}"
            )

    return private_db


def get_dataset_credentials(
    private_db_credentials: List[PrivateDBCredentials],
    db_type: PrivateDatabaseType,
    credentials_name: str,
) -> PrivateDBCredentials:
    """
    Search the list of private database credentials and
    returns the one that matches the database type and
    credentials name.

    Args:
        private_db_credentials (List[PrivateDBCredentials]):\
            The list of private database credentials.
        db_type (PrivateDatabaseType): The type of the database.
        ds_infos (Dict[str, str]): _description_

    Raises:
        InternalServerException: If the credentials are not found.

    Returns:
        PrivateDBCredentials: The matching credentials.
    """

    if db_type == PrivateDatabaseType.S3:
        for c in private_db_credentials:
            if isinstance(c, S3CredentialsConfig) and (
                credentials_name == c.credentials_name
            ):
                return c

    raise InternalServerException(
        "Could not find credentials for private dataset."
        "Please contact server administrator."
    )
