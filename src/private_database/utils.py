from private_database.private_database import PrivateDatabase
from private_database.constant_path import ConstantPath
from private_database.s3_database import S3Database
from utils.constants import CONSTANT_PATH_DB, S3_DB


def private_database_factory(
    dataset_name: str, admin_database
) -> PrivateDatabase:
    """
    Returns the appropriate database class based on dataset storage location
    """
    # database_type = admin_database.get_database_type(dataset_name)
    database_type = admin_database.get_dataset_field(
        dataset_name, "database_field"
    )

    if database_type == CONSTANT_PATH_DB:
        dataset_path = admin_database.get_dataset_field(
            dataset_name, "dataset_path"
        )
        private_db = ConstantPath(dataset_path)
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
