from private_database.private_database import PrivateDatabase
from private_database.constant_path import ConstantPath
from utils.constants import CONSTANT_PATH_DB


def private_database_factory(
    dataset_name: str, admin_database
) -> PrivateDatabase:
    """
    Returns the appropriate database class based on dataset storage location
    """
    database_type = admin_database.get_database_type(dataset_name)

    if database_type == CONSTANT_PATH_DB:
        private_db = ConstantPath(dataset_name)
    else:
        raise (
            f"Unknown database type {database_type} \
                for dataset {dataset_name}."
        )
    return private_db
