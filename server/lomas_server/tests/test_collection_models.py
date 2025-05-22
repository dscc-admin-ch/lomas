import unittest
from typing import Any

import pytest

from lomas_core.models.collections import (
    BooleanMetadata,
    BoundedColumnMetadata,
    CategoricalColumnMetadata,
    DatetimeMetadata,
    FloatMetadata,
    IntCategoricalMetadata,
    IntMetadata,
    Metadata,
    StrCategoricalMetadata,
    StrMetadata,
)


class TestMetadataModel(unittest.TestCase):
    """Tests for the input validation of dataset metadata."""

    def test_categories(self) -> None:
        """Test categories validation."""
        input_str = {
            "type": "string",
            "cardinality": 4,
            "categories": ["a", "b", "c", "d"],
        }

        str_categorical_metadata = StrCategoricalMetadata.model_validate(input_str)

        assert isinstance(str_categorical_metadata, StrCategoricalMetadata)
        assert isinstance(str_categorical_metadata, CategoricalColumnMetadata)

        input_int = {
            "type": "int",
            "precision": 32,
            "cardinality": 4,
            "categories": [5, 6, 7, 8],
        }

        int_categorical_metadata = IntCategoricalMetadata.model_validate(input_int)

        assert isinstance(int_categorical_metadata, IntCategoricalMetadata)
        assert isinstance(int_categorical_metadata, CategoricalColumnMetadata)

    def test_categories_required(self) -> None:
        """Test categories required."""
        input_str = {"type": "string", "cardinality": 4}

        with pytest.raises(ValueError):
            StrCategoricalMetadata.model_validate(input_str)

    def test_categories_match_type(self) -> None:
        """Test categories match column type."""
        input_str = {
            "type": "string",
            "cardinality": 4,
            "categories": [1, 2, 3, 4],
        }

        with pytest.raises(ValueError):
            StrCategoricalMetadata.model_validate(input_str)

    def test_categories_match_cardinality(self) -> None:
        """Test categories match cardinality."""
        input_int = {"type": "int", "cardinality": 4, "categories": [1, 2, 3]}

        with pytest.raises(ValueError):
            IntCategoricalMetadata.model_validate(input_int)

    def test_boolean_column(self) -> None:
        """Test_boolean_column."""
        input_bool = {
            "type": "boolean",
        }

        metadata = BooleanMetadata.model_validate(input_bool)
        assert isinstance(metadata, BooleanMetadata)

    def test_int_column(self) -> None:
        """Test_int_column."""
        input_int = {"type": "int", "precision": 32, "lower": 0, "upper": 10}

        metadata = IntMetadata.model_validate(input_int)
        assert isinstance(metadata, IntMetadata)
        assert isinstance(metadata, BoundedColumnMetadata)

    def test_float_column(self) -> None:
        """Test_float_column."""
        input_float = {
            "type": "float",
            "precision": 64,
            "lower": 0,
            "upper": 10.5,
        }

        metadata = FloatMetadata.model_validate(input_float)
        assert isinstance(metadata, FloatMetadata)
        assert isinstance(metadata, BoundedColumnMetadata)

    def test_datetime_column(self) -> None:
        """Test_datetime_column."""
        input_datetime = {
            "type": "datetime",
            "lower": "2000-01-01",
            "upper": "2001-01-01",
        }

        metadata = DatetimeMetadata.model_validate(input_datetime)
        assert isinstance(metadata, DatetimeMetadata)
        assert isinstance(metadata, BoundedColumnMetadata)

        input_datetime = {
            "type": "datetime",
            "lower": "2001-01-01",
            "upper": "2000-01-01",
        }
        with pytest.raises(ValueError):
            DatetimeMetadata.model_validate(input_datetime)

    def test_precision(self) -> None:
        """Test precision can only be 32 or 64."""
        input_int = {"type": int, "precision": 20, "lower": 0, "upper": 10}

        with pytest.raises(ValueError):
            IntMetadata.model_validate(input_int)

    def test_lower_upper_bounded(self) -> None:
        """Test lower is smaller than upper and of right type."""
        input_int = {"type": "int", "precision": 32, "lower": 0, "upper": -1}

        with pytest.raises(ValueError):
            IntMetadata.model_validate(input_int)

        input_int["upper"] = 10.5
        with pytest.raises(ValueError):
            IntMetadata.model_validate(input_int)

    def test_standard_metadata_fields(self) -> None:
        """Test standard metadata fields."""
        input_metadata = {
            "max_ids": 1,
            "rows": 100,
            "row_privacy": False,
            "columns": {},
        }

        metadata = Metadata.model_validate(input_metadata)
        assert isinstance(metadata, Metadata)
        assert not metadata.censor_dims

        input_metadata["censor_dims"] = True
        metadata = Metadata.model_validate(input_metadata)
        assert metadata.censor_dims

        input_metadata["rows"] = 0
        with pytest.raises(ValueError):
            Metadata.model_validate(input_metadata)

        input_metadata["rows"] = 100
        input_metadata["max_ids"] = -1
        with pytest.raises(ValueError):
            Metadata.model_validate(input_metadata)

    def test_metadata_columns_discriminator(self) -> None:
        """Test metadata column discriminator."""
        input_metadata: dict[str, Any] = {
            "max_ids": 1,
            "rows": 100,
            "row_privacy": False,
            "columns": {
                "str": {"type": "string"},
                "str_cat": {
                    "type": "string",
                    "cardinality": 2,
                    "categories": ["a", "b"],
                },
                "int": {
                    "type": "int",
                    "precision": 32,
                    "lower": 0,
                    "upper": 10,
                },
                "int_cat": {
                    "type": "int",
                    "cardinality": 2,
                    "categories": [1, 2],
                    "precision": 32,
                },
                "float": {
                    "type": "float",
                    "precision": 64,
                    "lower": 0.5,
                    "upper": 1.2,
                },
                "boolean": {"type": "boolean"},
                "datetime": {
                    "type": "datetime",
                    "lower": "2000-01-01",
                    "upper": "2001-01-01",
                },
            },
        }

        metadata = Metadata.model_validate(input_metadata)

        assert isinstance(metadata.columns["str"], StrMetadata)
        assert isinstance(metadata.columns["str_cat"], StrCategoricalMetadata)
        assert isinstance(metadata.columns["int"], IntMetadata)
        assert isinstance(metadata.columns["int_cat"], IntCategoricalMetadata)
        assert isinstance(metadata.columns["float"], FloatMetadata)
        assert isinstance(metadata.columns["boolean"], BooleanMetadata)
        assert isinstance(metadata.columns["datetime"], DatetimeMetadata)

        input_metadata["columns"]["some_type"] = {"type": "some_type"}
        with pytest.raises(ValueError):
            Metadata.model_validate(input_metadata)
