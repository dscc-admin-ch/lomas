from admin_database.admin_database import AdminDatabase
from constants import PrivateDatabaseType
from private_dataset.path_dataset import PathDataset
from private_dataset.private_dataset import PrivateDataset
from private_dataset.s3_dataset import S3Dataset
from utils.error_handler import InternalServerException


def private_dataset_factory(
    dataset_name: str, admin_database: AdminDatabase
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
            s3_parameters["s3_bucket"] = admin_database.get_dataset_field(
                dataset_name, "s3_bucket"
            )
            s3_parameters["s3_key"] = admin_database.get_dataset_field(
                dataset_name, "s3_key"
            )
            s3_parameters["s3_endpoint"] = admin_database.get_dataset_field(
                dataset_name, "endpoint_url"
            )
            s3_parameters[
                "s3_aws_access_key_id"
            ] = admin_database.get_dataset_field(
                dataset_name, "aws_access_key_id"
            )
            s3_parameters[
                "aws_secret_access_key"
            ] = admin_database.get_dataset_field(
                dataset_name, "aws_secret_access_key"
            )
            private_db = S3Dataset(ds_metadata, s3_parameters)
        case _:
            raise InternalServerException(
                f"Unknown database type: {database_type}"
            )

    return private_db
