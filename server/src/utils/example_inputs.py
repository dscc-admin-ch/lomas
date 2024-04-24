# Dummy queries
DUMMY_EPSILON = 100.0
DUMMY_DELTA = 0.99

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

# DUMMY dataset name
PENGUIN_DATASET = "PENGUIN"


example_get_admin_db_data = {
    "dataset_name": PENGUIN_DATASET,
}

example_get_dummy_dataset = {
    "dataset_name": PENGUIN_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": PENGUIN_DATASET,
    "epsilon": 0.1,
    "delta": 0.00001,
    "mechanisms": {"count": "gaussian"},
    "postprocess": True,
}

example_dummy_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": PENGUIN_DATASET,
    "epsilon": DUMMY_EPSILON,
    "delta": DUMMY_DELTA,
    "mechanisms": {"count": "gaussian"},
    "postprocess": False,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql_cost = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": PENGUIN_DATASET,
    "epsilon": 0.1,
    "delta": 0.00001,
    "mechanisms": {"count": "gaussian"},
}

meas_pipeline = '{"version": "0.8.0", "ast": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "partial_chain", "lhs": {"_type": "constructor", "func": "make_chain_tt", "module": "combinators", "args": [{"_type": "constructor", "func": "make_select_column", "module": "transformations", "kwargs": {"key": "bill_length_mm", "TOA": "String"}}, {"_type": "constructor", "func": "make_split_dataframe", "module": "transformations", "kwargs": {"separator": ",", "col_names": {"_type": "list", "_items": ["species", "island", "bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g", "sex"]}}}]}, "rhs": {"_type": "constructor", "func": "then_cast_default", "module": "transformations", "kwargs": {"TOA": "f64"}}}, "rhs": {"_type": "constructor", "func": "then_clamp", "module": "transformations", "kwargs": {"bounds": [30.0, 65.0]}}}, "rhs": {"_type": "constructor", "func": "then_resize", "module": "transformations", "kwargs": {"size": 346, "constant": 43.61}}}, "rhs": {"_type": "constructor", "func": "then_variance", "module": "transformations"}}, "rhs": {"_type": "constructor", "func": "then_laplace", "module": "measurements", "kwargs": {"scale": 5.0}}}}'  # noqa: E501

example_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": meas_pipeline,
    "input_data_type": "df",
    "fixed_delta": 1e-6,
}

example_dummy_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": meas_pipeline,
    "input_data_type": "df",
    "fixed_delta": 1e-6,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}
