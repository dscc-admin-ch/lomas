from typing import Dict, List

from admin_database.admin_database import AdminDatabase
from constants import PrivateDatabaseType
from private_dataset.path_dataset import PathDataset
from private_dataset.private_dataset import PrivateDataset
from private_dataset.s3_dataset import S3Dataset
from utils.config import PrivateDBCredentials, S3CredentialsConfig
from utils.error_handler import InternalServerException


def private_dataset_factory(
    dataset_name: str,
    admin_database: AdminDatabase,
    private_db_credentials: List[PrivateDBCredentials],
) -> PrivateDataset:
    """
    Returns the appropriate dataset class based on dataset storage location

    Args:
        dataset_name (str): The dataset name.
        admin_database (AdminDatabase): An initialized instance
            of AdminDatabase.

    Raises:
        InternalServerException: If the dataset type does not exist.

    Returns:
        PrivateDataset: The PrivateDataset instance for this dataset.
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
            private_db = PathDataset(ds_metadata, dataset_path)
        case PrivateDatabaseType.S3:
            s3_parameters = {}
            s3_parameters["bucket"] = admin_database.get_dataset_field(
                dataset_name, "bucket"
            )
            s3_parameters["key"] = admin_database.get_dataset_field(
                dataset_name, "key"
            )
            s3_parameters["endpoint_url"] = admin_database.get_dataset_field(
                dataset_name, "endpoint_url"
            )

            s3_parameters["credentials_name"] = (
                admin_database.get_dataset_field(
                    dataset_name, "credentials_name"
                )
            )

            db_type = "s3"
            credentials = get_dataset_credentials(
                private_db_credentials, db_type, s3_parameters
            )

            private_db = S3Dataset(ds_metadata, credentials)
        case _:
            raise InternalServerException(
                f"Unknown database type: {database_type}"
            )

    return private_db


def get_dataset_credentials(
    private_db_credentials: List[PrivateDBCredentials],
    db_type: str,
    ds_infos: Dict[str, str],
) -> PrivateDBCredentials:
    """_summary_

    Args:
        private_db_credentials (List[PrivateDBCredentials]): _description_
        db_type (str): _description_
        ds_infos (Dict[str, str]): _description_

    Raises:
        InternalServerException: _description_

    Returns:
        PrivateDBCredentials: _description_
    """

    if db_type == "s3":
        for c in private_db_credentials:
            if isinstance(c, S3CredentialsConfig) and (
                ds_infos["credentials_name"] == c.credentials_name
            ):
                c.endpoint_url = ds_infos["endpoint_url"]
                c.bucket = ds_infos["bucket"]
                c.key = ds_infos["key"]
                return c

    raise InternalServerException(
        "Could not find credentials for private dataset."
        "Please contact server administrator."
    )
