from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

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


class MetadataOfPathDB(MetadataOfDataset):
    """BaseModel for metadata of a dataset with PATH_DB"""

    database_type: Literal[PrivateDatabaseType.PATH]  # type: ignore
    metadata_path: str


class MetadataOfS3DB(MetadataOfDataset):
    """BaseModel for metadata of a dataset with S3_DB"""

    database_type: Literal[PrivateDatabaseType.S3]  # type: ignore
    endpoint_url: str
    bucket: str
    key: str
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    credentials_name: str


class Dataset(BaseModel):
    """BaseModel for a dataset"""

    dataset_name: str
    metadata: Union[MetadataOfPathDB, MetadataOfS3DB] = Field(
        ..., discriminator="database_type"
    )


class DatasetOfPathDB(Dataset):
    """BaseModel for a local dataset"""

    database_type: Literal[PrivateDatabaseType.PATH]  # type: ignore
    dataset_path: str


class DatasetOfS3DB(Dataset):
    """BaseModel for a dataset on S3"""

    database_type: Literal[PrivateDatabaseType.S3]  # type: ignore
    endpoint_url: str
    bucket: str
    key: str
    credentials_name: str


class DatasetsCollection(BaseModel):
    """BaseModel for datasets collection"""

    datasets: Annotated[
        List[Union[DatasetOfPathDB, DatasetOfS3DB]],
        Field(discriminator="database_type"),
    ]


class Metadata(BaseModel):
    """BaseModel for a metadata format"""

    max_ids: int
    row_privacy: bool
    censor_dims: Optional[bool] = False
    columns: Dict[str, Dict[str, Union[int, float, str, List[str]]]]
