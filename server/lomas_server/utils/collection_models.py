from typing import Dict, List, Union

from pydantic import BaseModel

from constants import PrivateDatabaseType


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

    database_type: PrivateDatabaseType


class MetadataOfPathDB(MetadataOfDataset):
    """BaseModel for metadata of a dataset with PATH_DB"""

    metadata_path: str


class MetadataOfS3DB(MetadataOfDataset):
    """BaseModel for metadata of a dataset with S3_DB"""

    s3_bucket: str
    s3_key: str
    endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str


class Dataset(BaseModel):
    """BaseModel for a dataset"""

    dataset_name: str
    database_type: PrivateDatabaseType
    metadata: Union[MetadataOfPathDB, MetadataOfS3DB]


class DatasetOfPathDB(Dataset):
    """BaseModel for a local dataset"""

    dataset_path: str


class DatasetOfS3DB(Dataset):
    """BaseModel for a dataset on S3"""

    s3_bucket: str
    s3_key: str
    endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str


class DatasetsCollection(BaseModel):
    """BaseModel for datasets collection"""

    datasets: List[Union[DatasetOfPathDB, DatasetOfS3DB]]


class Metadata(BaseModel):
    """BaseModel for a metadata format"""

    max_ids: int
    row_privacy: bool
    columns: Dict[str, Dict[str, Union[int, float, str, List[str]]]]
