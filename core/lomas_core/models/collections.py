from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Discriminator, Field, Tag, model_validator

from lomas_core.models.constants import (
    CARDINALITY_FIELD,
    CATEGORICAL_TYPE_PREFIX,
    DB_TYPE_FIELD,
    TYPE_FIELD,
    MetadataColumnType,
    Precision,
    PrivateDatabaseType,
)

# Dataset of User
# -----------------------------------------------------------------------------


class DatasetOfUser(BaseModel):
    """BaseModel for informations of a user on a dataset."""

    dataset_name: str
    initial_epsilon: float
    initial_delta: float
    total_spent_epsilon: float
    total_spent_delta: float


# User
# -----------------------------------------------------------------------------


class User(BaseModel):
    """BaseModel for a user in a user collection."""

    user_name: str
    may_query: bool
    datasets_list: List[DatasetOfUser]


class UserCollection(BaseModel):
    """BaseModel for users collection."""

    users: List[User]


# Dataset Access Data
# -----------------------------------------------------------------------------


class DSAccess(BaseModel):
    """BaseModel for access info to a private dataset."""

    database_type: str


class DSPathAccess(DSAccess):
    """BaseModel for a local dataset."""

    database_type: Literal[PrivateDatabaseType.PATH]  # type: ignore
    path: str


class DSS3Access(DSAccess):
    """BaseModel for a dataset on S3."""

    database_type: Literal[PrivateDatabaseType.S3]  # type: ignore
    endpoint_url: str
    bucket: str
    key: str
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    credentials_name: str


class DSInfo(BaseModel):
    """BaseModel for a dataset."""

    dataset_name: str
    dataset_access: Annotated[
        Union[DSPathAccess, DSS3Access], Field(discriminator=DB_TYPE_FIELD)
    ]
    metadata_access: Annotated[
        Union[DSPathAccess, DSS3Access], Field(discriminator=DB_TYPE_FIELD)
    ]


class DatasetsCollection(BaseModel):
    """BaseModel for datasets collection."""

    datasets: List[DSInfo]


# Metadata
# -----------------------------------------------------------------------------


class ColumnMetadata(BaseModel):
    """Base model for column metadata."""

    private_id: bool = False
    nullable: bool = False
    # See issue #323 for checking this and validating.

    max_partition_length: Optional[Annotated[int, Field(gt=0)]] = None
    max_influenced_partitions: Optional[Annotated[int, Field(gt=0)]] = None
    max_partition_contributions: Optional[Annotated[int, Field(gt=0)]] = None


class StrMetadata(ColumnMetadata):
    """Model for string metadata."""

    type: Literal[MetadataColumnType.STRING]


class CategoricalColumnMetadata(ColumnMetadata):
    """Model for categorical column metadata."""

    @model_validator(mode="after")
    def validate_categories(self):
        """Makes sure number of categories matches cardinality."""
        if len(self.categories) != self.cardinality:
            raise ValueError("Number of categories should be equal to cardinality.")
        return self


class StrCategoricalMetadata(CategoricalColumnMetadata):
    """Model for categorical string metadata."""

    type: Literal[MetadataColumnType.STRING]
    cardinality: int
    categories: List[str]


class BoundedColumnMetadata(ColumnMetadata):
    """Model for columns with bounded data."""

    @model_validator(mode="after")
    def validate_bounds(self):
        """Validates column bounds."""
        if (
            self.lower is not None
            and self.upper is not None
            and self.lower > self.upper
        ):
            raise ValueError("Lower bound cannot be larger than upper bound.")

        return self


class IntMetadata(BoundedColumnMetadata):
    """Model for integer column metadata."""

    type: Literal[MetadataColumnType.INT]
    precision: Precision
    lower: int
    upper: int


class IntCategoricalMetadata(CategoricalColumnMetadata):
    """Model for integer categorical column metadata."""

    type: Literal[MetadataColumnType.INT]
    precision: Precision
    cardinality: int
    categories: List[int]


class FloatMetadata(BoundedColumnMetadata):
    """Model for float column metadata."""

    type: Literal[MetadataColumnType.FLOAT]
    precision: Precision
    lower: float
    upper: float


class BooleanMetadata(ColumnMetadata):
    """Model for boolean column metadata."""

    type: Literal[MetadataColumnType.BOOLEAN]


class DatetimeMetadata(BoundedColumnMetadata):
    """Model for datetime column metadata."""

    type: Literal[MetadataColumnType.DATETIME]
    lower: datetime
    upper: datetime


def get_column_metadata_discriminator(v: Any) -> str:
    """Discriminator function for determining the type of column metadata.

    Args:
        v (Any): The unparsed column metadata (either dict or class object)

    Raises:
        ValueError: If the column type cannot be found.

    Returns:
        str: The metadata string type.
    """
    if isinstance(v, dict):
        col_type = v.get(TYPE_FIELD)
    else:
        col_type = getattr(v, TYPE_FIELD)

    if (
        col_type
        in (
            MetadataColumnType.STRING,
            MetadataColumnType.INT,
        )
    ) and (
        ((isinstance(v, dict)) and CARDINALITY_FIELD in v)
        or (hasattr(v, CARDINALITY_FIELD))
    ):
        col_type = f"{CATEGORICAL_TYPE_PREFIX}{col_type}"

    if not isinstance(col_type, str):
        raise ValueError("Could not find column type.")

    return col_type


class Metadata(BaseModel):
    """BaseModel for a metadata format."""

    max_ids: Annotated[int, Field(gt=0)]
    rows: Annotated[int, Field(gt=0)]
    row_privacy: bool
    censor_dims: Optional[bool] = False
    columns: Dict[
        str,
        Annotated[
            Union[
                Annotated[StrMetadata, Tag(MetadataColumnType.STRING)],
                Annotated[StrCategoricalMetadata, Tag(MetadataColumnType.CAT_STRING)],
                Annotated[IntMetadata, Tag(MetadataColumnType.INT)],
                Annotated[IntCategoricalMetadata, Tag(MetadataColumnType.CAT_INT)],
                Annotated[FloatMetadata, Tag(MetadataColumnType.FLOAT)],
                Annotated[BooleanMetadata, Tag(MetadataColumnType.BOOLEAN)],
                Annotated[DatetimeMetadata, Tag(MetadataColumnType.DATETIME)],
            ],
            Discriminator(get_column_metadata_discriminator),
        ],
    ]
