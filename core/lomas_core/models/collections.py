from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl

from lomas_core.models.constants import DB_TYPE_FIELD, PrivateDatabaseType

# Dataset of User
# -----------------------------------------------------------------------------


class DatasetOfUser(BaseModel):
    """BaseModel for informations of a user on a dataset."""

    dataset_name: str
    initial_epsilon: float
    initial_delta: float
    total_spent_epsilon: float = Field(default=0.0)
    total_spent_delta: float = Field(default=0.0)


# User
# -----------------------------------------------------------------------------


class UserId(BaseModel):
    """BaseModel for user identification."""

    name: str
    email: str
    client_secret: Annotated[
        str | None,
        Field(default=None, exclude=True),  # exclude the field at serialization for security reasons
    ]


class User(BaseModel):
    """BaseModel for a user in a user collection."""

    id: UserId
    may_query: bool
    admin: bool = False
    datasets_list: list[DatasetOfUser]


class UserCollection(BaseModel):
    """BaseModel for users collection."""

    users: list[User]


# Dataset Access Data
# -----------------------------------------------------------------------------


class DSPathAccess(BaseModel):
    """BaseModel for a local dataset."""

    database_type: Literal[PrivateDatabaseType.PATH]
    path: HttpUrl | Path  # force check Path should be relative ? or move prefix logic closer


class DSS3Access(BaseModel):
    """BaseModel for a dataset on S3."""

    database_type: Literal[PrivateDatabaseType.S3]
    endpoint_url: HttpUrl
    bucket: str
    key: str
    access_key_id: str | None = None
    secret_access_key: str | None = None
    credentials_name: str


class DSInfo(BaseModel):
    """BaseModel for a dataset."""

    dataset_name: str
    dataset_access: Annotated[DSPathAccess | DSS3Access, Field(discriminator=DB_TYPE_FIELD)]
    metadata_access: Annotated[DSPathAccess | DSS3Access, Field(discriminator=DB_TYPE_FIELD)]


class DatasetsCollection(BaseModel):
    """BaseModel for datasets collection."""

    datasets: list[DSInfo]
