from lomas_server.constants import (
    DIFFPRIVLIB_PIPELINE,
    OPENDP_PIPELINE,
    SSynthGanSynthesizer,
)

# Dummy queries
DUMMY_EPSILON = 100.0
DUMMY_DELTA = 0.99

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

# Query constants
PENGUIN_DATASET = "PENGUIN"
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
SNSYNTH_NB_SAMPLES = 200


def make_dummy(example_query):
    """Make dummy example dummy query based on example query"""
    example_query_dummy = dict(example_query)
    example_query_dummy["dummy_nb_rows"] = DUMMY_NB_ROWS
    example_query_dummy["dummy_seed"] = DUMMY_SEED
    return example_query_dummy


# Lomas logic
example_get_admin_db_data = {
    "dataset_name": PENGUIN_DATASET,
}

example_get_dummy_dataset = {
    "dataset_name": PENGUIN_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

# Smartnoise-SQL
example_smartnoise_sql_cost = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "mechanisms": DP_MECHANISM,
}

example_smartnoise_sql = dict(example_smartnoise_sql_cost)
example_smartnoise_sql["postprocess"] = True

example_dummy_smartnoise_sql = make_dummy(example_smartnoise_sql)

# Smartnoise-Synth
example_smartnoise_synth_cost = {
    "dataset_name": PENGUIN_DATASET,
    "synth_name": SSynthGanSynthesizer.DP_CTGAN,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "select_cols": [],
    "synth_params": {
        "embedding_dim": 128,
        "batch_size": 50,
        "epochs": 5,
    },
    "nullable": True,
    "constraints": "",
}
example_smartnoise_synth_query = dict(example_smartnoise_synth_cost)
example_smartnoise_synth_query["return_model"] = True
example_smartnoise_synth_query["condition"] = ""
example_smartnoise_synth_query["nb_samples"] = SNSYNTH_NB_SAMPLES

example_dummy_smartnoise_synth_query = make_dummy(
    example_smartnoise_synth_query
)

# OpenDP
example_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": OPENDP_PIPELINE,
    "fixed_delta": QUERY_DELTA,
}
example_dummy_opendp = make_dummy(example_opendp)

# DiffPrivLib
example_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_PIPELINE,
    "feature_columns": FEATURE_COLUMNS,
    "target_columns": TARGET_COLUMNS,
    "test_size": TEST_SIZE,
    "test_train_split_seed": SPLIT_SEED,
    "imputer_strategy": IMPUTER_STRATEGY,
}
example_dummy_diffprivlib = make_dummy(example_diffprivlib)
