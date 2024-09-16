from datetime import datetime
from enum import IntEnum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Discriminator, Field, Tag, model_validator

from lomas_server.constants import PrivateDatabaseType


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


class ColumnMetadata(BaseModel):
    """Base model for column metadata"""

    private_id: bool = False
    nullable: bool = False
    # TODO create validator and test these, see issue #323
    max_partition_length: Optional[Annotated[int, Field(gt=0)]] = None
    max_influenced_partitions: Optional[Annotated[int, Field(gt=0)]] = None
    max_partition_contributions: Optional[Annotated[int, Field(gt=0)]] = None


class StrMetadata(ColumnMetadata):
    """Model for string metadata"""

    type: Literal["string"]


class CategoricalColumnMetadata(ColumnMetadata):
    """Model for categorical column metadata"""

    @model_validator(mode="after")
    def validate_categories(self):
        """Makes sure number of categories matches cardinality."""
        if len(self.categories) != self.cardinality:
            raise ValueError(
                "Number of categories should be equal to cardinality."
            )
        return self


class StrCategoricalMetadata(CategoricalColumnMetadata):
    """Model for categorical string metadata"""

    type: Literal["string"]
    cardinality: int
    categories: List[str]


class Precision(IntEnum):
    """Precision of integer and float data"""

    SINGLE = 32
    DOUBLE = 64


class BoundedColumnMetadata(ColumnMetadata):
    """Model for columns with bounded data"""

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
    """Model for integer column metadata"""

    type: Literal["int"]
    precision: Precision
    lower: int
    upper: int


class IntCategoricalMetadata(CategoricalColumnMetadata):
    """Model for integer categorical column metadata"""

    type: Literal["int"]
    precision: Precision
    cardinality: int
    categories: List[int]


class FloatMetadata(BoundedColumnMetadata):
    """Model for float column metadata"""

    type: Literal["float"]
    precision: Precision
    lower: float
    upper: float


class BooleanMetadata(ColumnMetadata):
    """Model for boolean column metadata"""

    type: Literal["boolean"]


class DatetimeMetadata(BoundedColumnMetadata):
    """Model for datetime column metadata"""

    type: Literal["datetime"]  # TODO make these constants, see issue #268
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
        col_type = v.get("type")
    else:
        col_type = getattr(v, "type")

    if (col_type in ("string", "int")) and (
        ((isinstance(v, dict)) and "cardinality" in v)
        or (hasattr(v, "cardinality"))
    ):
        col_type = f"categorical_{col_type}"

    if not isinstance(col_type, str):
        raise ValueError("Could not find column type.")

    return col_type


class Metadata(BaseModel):
    """BaseModel for a metadata format"""

    max_ids: Annotated[int, Field(gt=0)]
    rows: Annotated[int, Field(gt=0)]
    row_privacy: bool
    censor_dims: Optional[bool] = False
    columns: Dict[
        str,
        Annotated[
            Union[
                Annotated[StrMetadata, Tag("string")],
                Annotated[StrCategoricalMetadata, Tag("categorical_string")],
                Annotated[IntMetadata, Tag("int")],
                Annotated[IntCategoricalMetadata, Tag("categorical_int")],
                Annotated[FloatMetadata, Tag("float")],
                Annotated[BooleanMetadata, Tag("boolean")],
                Annotated[DatetimeMetadata, Tag("datetime")],
            ],
            Discriminator(get_column_metadata_discriminator),
        ],
    ]
