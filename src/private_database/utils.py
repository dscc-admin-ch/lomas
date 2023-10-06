from private_database.private_database import PrivateDatabase
from private_database.remote_http_csv_dataset import RemoteHTTPCSVDataset
from private_database.s3_dataset import S3Database
from utils.constants import REMOTE_HTTP_DB, S3_DB


def private_database_factory(
    dataset_name: str, admin_database
) -> PrivateDatabase:
    """
    Returns the appropriate database class based on dataset storage location
    """
    # database_type = admin_database.get_database_type(dataset_name)
    database_type = admin_database.get_dataset_field(
        dataset_name, "database_type"
    )

    if database_type == REMOTE_FILE_DB:
        dataset_path = admin_database.get_dataset_field(
            dataset_name, "dataset_path"
        )
        private_db = RemoteHTTPPathDataset(dataset_path)
    elif database_type == S3_DB:
        s3_bucket = admin_database.get_dataset_field(dataset_name, "s3_bucket")
        s3_key = admin_database.get_dataset_field(dataset_name, "s3_key")
        private_db = S3Database(s3_bucket, s3_key)
    else:
        raise (
            f"Unknown database type {database_type} \
            for dataset {dataset_name}."
        )
    return private_db
