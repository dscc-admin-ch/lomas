from lomas_core.constants import SSynthGanSynthesizer

from lomas_server.constants import (
    DIFFPRIVLIB_VERSION,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    OPENDP_VERSION,
)

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
    """Make dummy example dummy query based on example query."""
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

example_dummy_smartnoise_synth_query = make_dummy(example_smartnoise_synth_query)

# OpenDP

# Example inputs
# -----------------------------------------------------------------------------
OPENDP_PIPELINE = (
    f'{{"version": "{OPENDP_VERSION}", '
    '"ast": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "constructor", '
    '"func": "make_chain_tt", '
    '"module": "combinators", '
    '"args": ['
    "{"
    '"_type": "constructor", '
    '"func": "make_select_column", '
    '"module": "transformations", '
    '"kwargs": {"key": "bill_length_mm", "TOA": "String"}'
    "}, {"
    '"_type": "constructor", '
    '"func": "make_split_dataframe", '
    '"module": "transformations", '
    '"kwargs": {"separator": ",", "col_names": {"_type": '
    '"list", "_items": ["species", "island", '
    '"bill_length_mm", "bill_depth_mm", "flipper_length_'
    'mm", "body_mass_g", "sex"]}}'
    "}]}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_cast_default", '
    '"module": "transformations", '
    '"kwargs": {"TOA": "f64"}'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_clamp", '
    '"module": "transformations", '
    '"kwargs": {"bounds": [30.0, 65.0]}'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_resize", '
    '"module": "transformations", '
    '"kwargs": {"size": 346, "constant": 43.61}'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_variance", '
    '"module": "transformations"'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_laplace", '
    '"module": "measurements", '
    '"kwargs": {"scale": 5.0}'
    "}}}"
)

example_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": OPENDP_PIPELINE,
    "fixed_delta": QUERY_DELTA,
}
example_dummy_opendp = make_dummy(example_opendp)

# DiffPrivLib
DIFFPRIVLIB_PIPELINE = (
    '{"module": "diffprivlib", '
    f'"version": "{DIFFPRIVLIB_VERSION}", '
    '"pipeline": ['
    "{"
    '"type": "_dpl_type:StandardScaler", '
    '"name": "scaler", '
    '"params": {'
    '"with_mean": true, '
    '"with_std": true, '
    '"copy": true, '
    '"epsilon": 0.5, '
    '"bounds": {'
    '"_tuple": true, '
    '"_items": [[30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0]]'
    "}, "
    '"random_state": null, '
    '"accountant": "_dpl_instance:BudgetAccountant"'
    "}"
    "}, "
    "{"
    '"type": "_dpl_type:LogisticRegression", '
    '"name": "classifier", '
    '"params": {'
    '"tol": 0.0001, '
    '"C": 1.0, '
    '"fit_intercept": true, '
    '"random_state": null, '
    '"max_iter": 100, '
    '"verbose": 0, '
    '"warm_start": false, '
    '"n_jobs": null, '
    '"epsilon": 1.0, '
    '"data_norm": 83.69469642643347, '
    '"accountant": "_dpl_instance:BudgetAccountant"'
    "}"
    "}"
    "]"
    "}"
)

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
