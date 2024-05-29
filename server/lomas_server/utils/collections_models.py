# type: ignore

from typing import Dict, List, Union
from pydantic import BaseModel

# from constants import PrivateDatabaseType


class DatasetOfUser(BaseModel):
    """BaseModel for informations of a user on a dataset"""

    dataset_name: str
    initial_epsilon: float
    initial_delta: float
    total_spent_epsilon: float
    total_spent_delta: float


class User(BaseModel):
    """BaseModel for a user in a user collection"""

    user_name: str
    may_query: bool
    datasets_list: List[DatasetOfUser]


class UserCollection(BaseModel):
    """BaseModel for users collection"""

    users: List[User]


class MetadataOfDataset(BaseModel):
    """BaseModel for metadata of a dataset"""

    database_type: str
    metadata_path: str = None
    s3_bucket: str = None
    s3_key: str = None
    endpoint_url: str = None
    aws_access_key_id: str = None
    aws_secret_access_key: str = None


class Dataset(BaseModel):
    """BaseModel for a dataset in a datasets collection"""

    dataset_name: str
    database_type: str
    dataset_path: str = None
    s3_bucket: str = None
    s3_key: str = None
    endpoint_url: str = None
    aws_access_key_id: str = None
    aws_secret_access_key: str = None
    metadata: MetadataOfDataset


class DatasetsCollection(BaseModel):
    """BaseModel for datasets collection"""

    datasets: List[Dataset]


class Metadata(BaseModel):
    """BaseModel for a metadata format"""

    max_ids: int
    row_privacy: bool
    columns: Dict[str, Dict[str, Union[int, float, str, List[str]]]]
