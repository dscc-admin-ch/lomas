from constants import (
    DIFFPRIVLIB_PIPELINE,
    OPENDP_PIPELINE,
    SSynthSynthesizer,
    SSynthTableTransStyle,
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
TABLE_TRANSFORMER_STYLE = SSynthTableTransStyle.GAN

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

example_dummy_smartnoise_sql = dict(example_smartnoise_sql)
example_dummy_smartnoise_sql["dummy_nb_rows"] = DUMMY_NB_ROWS
example_dummy_smartnoise_sql["dummy_seed"] = DUMMY_SEED

example_smartnoise_sql_cost = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "mechanisms": DP_MECHANISM,
}

example_smartnoise_synth = {
    "dataset_name": PENGUIN_DATASET,
    "synth_name": SSynthSynthesizer.DP_CTGAN,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "select_cols": [],
    "synth_params": {
        "embedding_dim": 128,
        "generator_dim": (256, 256),
        "discriminator_dim": (256, 256),
        "batch_size": 50,
    },
    "nullable": True,
    "table_transformer_style": TABLE_TRANSFORMER_STYLE,
    "constraints": {},
}
example_dummy_smartnoise_synth = dict(example_smartnoise_synth)
example_dummy_smartnoise_synth["dummy_nb_rows"] = DUMMY_NB_ROWS
example_dummy_smartnoise_synth["dummy_seed"] = DUMMY_SEED

example_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": OPENDP_PIPELINE,
    "fixed_delta": QUERY_DELTA,
}

example_dummy_opendp = dict(example_opendp)
example_dummy_opendp["dummy_nb_rows"] = DUMMY_NB_ROWS
example_dummy_opendp["dummy_seed"] = DUMMY_SEED


example_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_PIPELINE,
    "feature_columns": FEATURE_COLUMNS,
    "target_columns": TARGET_COLUMNS,
    "test_size": TEST_SIZE,
    "test_train_split_seed": SPLIT_SEED,
    "imputer_strategy": IMPUTER_STRATEGY,
}

example_dummy_diffprivlib = dict(example_diffprivlib)
example_dummy_diffprivlib["dummy_nb_rows"] = DUMMY_NB_ROWS
example_dummy_diffprivlib["dummy_seed"] = DUMMY_SEED
