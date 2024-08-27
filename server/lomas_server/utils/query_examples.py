from constants import (
    DIFFPRIVLIB_PIPELINE,
    OPENDP_PIPELINE,
    OPENDP_POLARS_PIPELINE,
    OPENDP_POLARS_PIPELINE_COVID,
)

# Dummy queries
DUMMY_EPSILON = 100.0
DUMMY_DELTA = 0.99

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

# Query constants
PENGUIN_DATASET = "PENGUIN"
FSO_INCOME_DATASET = "FSO_INCOME_SYNTHETIC"
QUERY_EPSILON = 0.1
QUERY_DELTA = 0.00001
SQL_QUERY = "SELECT COUNT(*) AS NB_ROW FROM df"
DP_MECHANISM = {"count": "gaussian"}
FEATURE_COLUMNS = [
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
]
TARGET_COLUMNS = ["species"]
SPLIT_SEED = 4
TEST_SIZE = 0.2
IMPUTER_STRATEGY = "drop"

example_get_admin_db_data = {
    "dataset_name": PENGUIN_DATASET,
}

example_get_dummy_dataset = {
    "dataset_name": PENGUIN_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "mechanisms": DP_MECHANISM,
    "postprocess": True,
}

example_dummy_smartnoise_sql = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": DUMMY_EPSILON,
    "delta": DUMMY_DELTA,
    "mechanisms": DP_MECHANISM,
    "postprocess": False,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql_cost = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "mechanisms": DP_MECHANISM,
}

example_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": OPENDP_PIPELINE,
    "pipeline_type": "legacy",  # TODO set constant
    "delta": QUERY_DELTA,
    "mechanism": None,
}

example_dummy_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": OPENDP_PIPELINE,
    "pipeline_type": "legacy",  # TODO set constant
    "delta": QUERY_DELTA,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
    "mechanism": None,
}

example_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_PIPELINE,
    "feature_columns": FEATURE_COLUMNS,
    "target_columns": TARGET_COLUMNS,
    "test_size": TEST_SIZE,
    "test_train_split_seed": SPLIT_SEED,
    "imputer_strategy": IMPUTER_STRATEGY,
}

example_dummy_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_PIPELINE,
    "feature_columns": FEATURE_COLUMNS,
    "target_columns": TARGET_COLUMNS,
    "test_train_split_seed": SPLIT_SEED,
    "test_size": TEST_SIZE,
    "imputer_strategy": IMPUTER_STRATEGY,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_opendp_polars = {
    "dataset_name": FSO_INCOME_DATASET,
    "opendp_json": OPENDP_POLARS_PIPELINE,
    "pipeline_type": "polars",  # TODO set constant
    "delta": QUERY_DELTA,
    "mechanism": "laplace",
}

example_opendp_polars_datetime = {
    "dataset_name": "COVID_SYNTHETIC",
    "opendp_json": OPENDP_POLARS_PIPELINE_COVID,
    "pipeline_type": "polars",  # TODO set constant
    "delta": QUERY_DELTA,
    "mechanism": "laplace",
}
