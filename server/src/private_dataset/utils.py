from admin_database.admin_database import AdminDatabase
from constants import PrivateDatabaseType
from private_dataset.local_dataset import LocalDataset
from private_dataset.private_dataset import PrivateDataset
from private_dataset.remote_http_dataset import RemoteHTTPDataset
from private_dataset.s3_dataset import S3Dataset
from utils.error_handler import InternalServerException


def private_dataset_factory(
    dataset_name: str, admin_database: AdminDatabase
) -> PrivateDataset:
    """
    Returns the appropriate database class based on dataset storage location
    """
    # database_type = admin_database.get_database_type(dataset_name)
    database_type = admin_database.get_dataset_field(
        dataset_name, "database_type"
    )

    ds_metadata = admin_database.get_dataset_metadata(dataset_name)

    match database_type:
        case PrivateDatabaseType.REMOTE_HTTP:
            dataset_url = admin_database.get_dataset_field(
                dataset_name, "dataset_url"
            )
            private_db = RemoteHTTPDataset(ds_metadata, dataset_url)
        case PrivateDatabaseType.S3:
            s3_bucket = admin_database.get_dataset_field(
                dataset_name, "s3_bucket"
            )
            s3_key = admin_database.get_dataset_field(dataset_name, "s3_key")
            s3_endpoint = admin_database.get_dataset_field(
                dataset_name, "endpoint_url"
            )
            s3_aws_access_key_id = admin_database.get_dataset_field(
                dataset_name, "aws_access_key_id"
            )
            s3_aws_secret_access_key = admin_database.get_dataset_field(
                dataset_name, "aws_secret_access_key"
            )
            private_db = S3Dataset(
                ds_metadata,
                s3_bucket,
                s3_key,
                s3_endpoint,
                s3_aws_access_key_id,
                s3_aws_secret_access_key,
            )
        case PrivateDatabaseType.LOCAL:
            dataset_path = admin_database.get_dataset_field(
                dataset_name, "dataset_path"
            )
            private_db = LocalDataset(ds_metadata, dataset_path)
        case _:
            raise InternalServerException(
                f"Unknown database type: {database_type}"
            )

    return private_db
