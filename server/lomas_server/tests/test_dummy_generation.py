# import unittest

# from dp_queries.dummy_dataset import make_dummy_dataset
# from utils.example_inputs import DUMMY_NB_ROWS, DUMMY_SEED


# class TestMakeDummyDataset(unittest.TestCase):
#     """
#     Tests for the generation of dummy datasets.
#     """

#     def test_cardinality_column(self) -> None:
#         """test_cardinality_column"""
#         metadata = {
#             "columns": {
#                 "col_card_cat": {  # cardinality + categories
#                     "type": "string",
#                     "cardinality": 3,
#                     "categories": ["x", "y", "z"],
#                 },
#                 "col_card_no_cat": {  # cardinality, no categories
#                     "type": "string",
#                     "cardinality": 3,
#                 },
#                 "col_no_card": {  # no cardinality
#                     "type": "string",
#                 },
#             }
#         }
#         df = make_dummy_dataset(metadata)

#         # Test shape
#         self.assertEqual(df.shape[0], DUMMY_NB_ROWS)
#         self.assertEqual(df.shape[1], len(metadata["columns"].keys()))

#         # Test cardinality type and categories
#         self.assertIn("col_card_cat", df.columns)
#         self.assertEqual(df["col_card_cat"].nunique(), 3)
#         self.assertEqual(set(df["col_card_cat"].values), {"x", "y", "z"})
#         assert isinstance(df["col_card_cat"], object)

#         # Test cardinality type and no categories
#         self.assertIn("col_card_no_cat", df.columns)
#         self.assertEqual(set(df["col_card_no_cat"].values), {"a", "b", "c"})
#         assert isinstance(df["col_card_no_cat"], object)

#         # Test cardinality type and no categories
#         self.assertIn("col_no_card", df.columns)
#         self.assertTrue(
#             df["col_no_card"].apply(lambda x: isinstance(x, str)).all()
#         )

#     def test_boolean_column(self) -> None:
#         """test_boolean_column"""

#         # Test a boolean column
#         metadata = {
#             "columns": {"col_bool": {"type": "boolean", "nullable": True}}
#         }
#         df = make_dummy_dataset(metadata)

#         # Test length
#         self.assertEqual(len(df), DUMMY_NB_ROWS)

#         # Test col generated is boolean
#         self.assertIn("col_bool", df.columns)
#         self.assertEqual(df.col_bool.dtypes.name, "boolean")

#     def test_float_column(self) -> None:
#         """test_float_column"""
#         lower_bound = 10.0
#         upper_bound = 20.0
#         metadata = {
#             "columns": {
#                 "col_float": {
#                     "type": "float",
#                     "upper": upper_bound,
#                     "lower": lower_bound,
#                 }
#             }
#         }
#         df = make_dummy_dataset(metadata)

#         # Test col generated is of type float
#         self.assertEqual(df.col_float.dtypes.name, "float64")

#         # Test within bounds
#         self.assertTrue((df["col_float"] >= lower_bound).all())
#         self.assertTrue((df["col_float"] <= upper_bound).all())

#     def test_int_column(self) -> None:
#         """test_int_column"""
#         lower_bound = 100
#         upper_bound = 120
#         metadata = {
#             "columns": {
#                 "col_int": {
#                     "type": "int",
#                     "upper": upper_bound,
#                     "lower": lower_bound,
#                 }
#             }
#         }
#         df = make_dummy_dataset(metadata)

#         # Test col generated is of type int
#         self.assertIn(df.col_int.dtypes.name, ["int32", "int64"])

#         # Test within bounds
#         self.assertTrue((df["col_int"] >= lower_bound).all())
#         self.assertTrue((df["col_int"] <= upper_bound).all())

#     def test_datetime_column(self) -> None:
#         """test_datetime_column"""
#         metadata = {"columns": {"col_datetime": {"type": "datetime"}}}
#         df = make_dummy_dataset(metadata)

#         # Test col generated is of type datetime
#         self.assertEqual(df.col_datetime.dtypes.name, "datetime64[ns]")

#         # Should not have any null values
#         self.assertFalse(df.col_datetime.isnull().values.any())

#     def test_nullable_column(self) -> None:
#         """test_nullable_column"""
#         metadata = {
#             "columns": {"col_nullable": {"type": "datetime", "nullable": True}}
#         }
#         df = make_dummy_dataset(metadata)

#         # Should have null values
#         self.assertTrue(df.col_nullable.isnull().values.any())

#     def test_seed(self) -> None:
#         """test_seed"""
#         # Test the behavior with different seeds
#         metadata = {"columns": {"col_int": {"type": "int", "nullable": True}}}
#         seed1 = DUMMY_SEED
#         seed2 = DUMMY_SEED + 1

#         df1 = make_dummy_dataset(metadata, seed=seed1)
#         df2 = make_dummy_dataset(metadata, seed=seed2)

#         # Check if datasets generated with different seeds are different
#         self.assertFalse(df1.equals(df2))

#         # Check if datasets generated with the same seed are identical
#         df1_copy = make_dummy_dataset(metadata, seed=seed1)
#         self.assertTrue(df1.equals(df1_copy))

#     def test_unknown_column(self) -> None:
#         """test_unknown_column"""
#         metadata = {
#             "columns": {
#                 "col_bool": {"type": "boolean", "nullable": True},
#                 "col_unknown": {"type": "unknown"},
#             }
#         }
#         df = make_dummy_dataset(metadata)

#         # Test col generated
#         self.assertIn("col_bool", df.columns)

#         # Test col not generated
#         self.assertNotIn("col_unknown", df.columns)
