from typing import Dict, List, Union
from pydantic import BaseModel

from constants import PrivateDatabaseType


class DatasetOfUser(BaseModel):
    """BaseModel for informations of a user on a dataset"""

    dataset_name: str
    initial_epsilon: float
    initial_delta: int
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
    """BaseModel for metadata of a dataset in datasets collection"""

    database_type: PrivateDatabaseType


class LocalMetadata(MetadataOfDataset):
    """BaseModel for local metadata of a dataset in datasets collection"""

    database_type: PrivateDatabaseType.PATH
    metadata_path: str


class S3Metadata(MetadataOfDataset):
    """BaseModel for local metadata of a dataset in datasets collection"""

    database_type: PrivateDatabaseType.S3
    s3_bucket: str
    s3_key: str
    endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str


class Dataset(BaseModel):
    """BaseModel for a dataset in datasets collection"""

    dataset_name: str
    database_type: PrivateDatabaseType
    metadata: Union[LocalMetadata, S3Metadata]


class LocalDataset(Dataset):
    """BaseModel for a local dataset in datasets collection"""

    database_type: PrivateDatabaseType.PATH
    dataset_path: str


class S3Dataset(Dataset):
    """BaseModel for an S3 dataset in datasets collection"""

    database_type: PrivateDatabaseType.S3
    s3_bucket: str
    s3_key: str
    endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str


class DatasetsCollection(BaseModel):
    """BaseModel for datasets collection"""

    datasets: List[Union[LocalDataset, S3Dataset]]


class Metadata(BaseModel):
    """BaseModel for a metadata format"""

    max_ids: int
    row_privacy: bool
    columns: Dict[str, Dict[str, Union[int, float, str, List[str]]]]
