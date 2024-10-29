from typing import List

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import DSPathAccess, DSS3Access
from lomas_core.models.config import PrivateDBCredentials, S3CredentialsConfig
from lomas_core.models.constants import PrivateDatabaseType

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.data_connector.path_connector import PathConnector
from lomas_server.data_connector.s3_connector import S3Connector


def data_connector_factory(
    dataset_name: str,
    admin_database: AdminDatabase,
    private_db_credentials: List[PrivateDBCredentials],
) -> DataConnector:
    """
    Returns the appropriate dataset class based on dataset storage location.

    Args:
        dataset_name (str): The dataset name.
        admin_database (AdminDatabase): An initialized instance
            of AdminDatabase.

    Raises:
        InternalServerException: If the dataset type does not exist.

    Returns:
        DataConnector: The DataConnector instance for this dataset.
    """
    ds_access = admin_database.get_dataset(dataset_name).dataset_access

    ds_metadata = admin_database.get_dataset_metadata(dataset_name)

    match ds_access:
        case DSPathAccess():
            return PathConnector(ds_metadata, ds_access.path)
        case DSS3Access():

            credentials = get_dataset_credentials(
                private_db_credentials,
                ds_access.database_type,
                ds_access.credentials_name,
            )

            if not isinstance(credentials, S3CredentialsConfig):
                raise InternalServerException("Could not get correct credentials")

            ds_access = DSS3Access.model_validate(ds_access)
            ds_access.access_key_id = credentials.access_key_id
            ds_access.secret_access_key = credentials.secret_access_key

            return S3Connector(ds_metadata, ds_access)
        case _:
            raise InternalServerException(
                f"Unknown database type: {ds_access.database_type}"
            )


def get_dataset_credentials(
    private_db_credentials: List[PrivateDBCredentials],
    db_type: PrivateDatabaseType,
    credentials_name: str,
) -> PrivateDBCredentials:
    """
    Search the list of private database credentials and.

    returns the one that matches the database type and
    credentials name.

    Args:
        private_db_credentials (Sequence[PrivateDBCredentials]):\
            The list of private database credentials.
        db_type (PrivateDatabaseType): The type of the database.

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
