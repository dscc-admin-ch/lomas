import unittest
from typing import Any

from lomas_core.models.collections import Metadata

from lomas_server.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_server.dp_queries.dummy_dataset import make_dummy_dataset


class TestMakeDummyDataset(unittest.TestCase):
    """Tests for the generation of dummy datasets."""

    metadata: dict[str, Any] = {
        "max_ids": 1,
        "rows": 100,
        "row_privacy": True,
        "columns": {},
    }

    def test_categorical_column(self) -> None:
        """Test_categorical_column."""
        self.metadata["columns"] = {
            "col_card_cat": {  # cardinality + categories
                "type": "string",
                "cardinality": 3,
                "categories": ["x", "y", "z"],
            }
        }
        metadata = Metadata.model_validate(self.metadata)
        df = make_dummy_dataset(metadata)

        # Test shape
        self.assertEqual(df.shape[0], DUMMY_NB_ROWS)
        self.assertEqual(df.shape[1], 1)

        # Test cardinality type and categories
        self.assertIn("col_card_cat", df.columns)
        self.assertEqual(df["col_card_cat"].nunique(), 3)
        self.assertEqual(set(df["col_card_cat"].values), {"x", "y", "z"})
        assert isinstance(df["col_card_cat"], object)

    def test_boolean_column(self) -> None:
        """Test_boolean_column."""

        # Test a boolean column
        self.metadata["columns"] = {"col_bool": {"type": "boolean", "nullable": True}}
        metadata = Metadata.model_validate(self.metadata)
        df = make_dummy_dataset(metadata)

        # Test length
        self.assertEqual(len(df), DUMMY_NB_ROWS)

        # Test col generated is boolean
        self.assertIn("col_bool", df.columns)
        self.assertEqual(df.col_bool.dtypes.name, "boolean")

    def test_float_column(self) -> None:
        """Test_float_column."""
        lower_bound = 10.0
        upper_bound = 20.0
        self.metadata["columns"] = {
            "col_float": {
                "type": "float",
                "precision": 32,
                "upper": upper_bound,
                "lower": lower_bound,
            }
        }
        metadata = Metadata.model_validate(self.metadata)
        df = make_dummy_dataset(metadata)

        # Test col generated is of type float
        self.assertEqual(df.col_float.dtypes.name, "float32")

        # Test within bounds
        self.assertTrue((df["col_float"] >= lower_bound).all())
        self.assertTrue((df["col_float"] <= upper_bound).all())

    def test_int_column(self) -> None:
        """Test_int_column."""
        lower_bound = 100
        upper_bound = 120
        self.metadata["columns"] = {
            "col_int": {
                "type": "int",
                "precision": 64,
                "upper": upper_bound,
                "lower": lower_bound,
            }
        }
        metadata = Metadata.model_validate(self.metadata)
        df = make_dummy_dataset(metadata)

        # Test col generated is of type int
        self.assertIn(df.col_int.dtypes.name, ["int64"])

        # Test within bounds
        self.assertTrue((df["col_int"] >= lower_bound).all())
        self.assertTrue((df["col_int"] <= upper_bound).all())

    def test_datetime_column(self) -> None:
        """Test_datetime_column."""
        self.metadata["columns"] = {
            "col_datetime": {
                "type": "datetime",
                "lower": "2000-01-01",
                "upper": "2010-01-01",
            }
        }
        metadata = Metadata.model_validate(self.metadata)
        df = make_dummy_dataset(metadata)

        # Test col generated is of type datetime
        self.assertEqual(df.col_datetime.dtypes.name, "datetime64[ns]")

        # Should not have any null values
        self.assertFalse(df.col_datetime.isnull().values.any())

    def test_nullable_column(self) -> None:
        """Test_nullable_column."""
        self.metadata["columns"] = {
            "col_nullable": {
                "type": "datetime",
                "nullable": True,
                "lower": "2000-01-01",
                "upper": "2010-01-01",
            }
        }
        metadata = Metadata.model_validate(self.metadata)
        df = make_dummy_dataset(metadata)

        # Should have null values
        self.assertTrue(df.col_nullable.isnull().values.any())

    def test_seed(self) -> None:
        """Test_seed."""
        # Test the behavior with different seeds
        self.metadata["columns"] = {
            "col_int": {
                "type": "int",
                "nullable": True,
                "precision": 32,
                "lower": 0,
                "upper": 100,
            }
        }
        metadata = Metadata.model_validate(self.metadata)
        seed1 = DUMMY_SEED
        seed2 = DUMMY_SEED + 1

        df1 = make_dummy_dataset(metadata, seed=seed1)
        df2 = make_dummy_dataset(metadata, seed=seed2)

        # Check if datasets generated with different seeds are different
        self.assertFalse(df1.equals(df2))

        # Check if datasets generated with the same seed are identical
        df1_copy = make_dummy_dataset(metadata, seed=seed1)
        self.assertTrue(df1.equals(df1_copy))
