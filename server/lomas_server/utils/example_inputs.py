# Dummy queries
DUMMY_EPSILON = 100.0
DUMMY_DELTA = 0.99

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

# DUMMY dataset name
PENGUIN_DATASET = "PENGUIN"
FSO_INCOME_DATASET = "FSO_INCOME_SYNTHETIC"
SMARTNOISE_QUERY_EPSILON = 0.1
SMARTNOISE_QUERY_DELTA = 0.00001

example_get_admin_db_data = {
    "dataset_name": PENGUIN_DATASET,
}

example_get_dummy_dataset = {
    "dataset_name": PENGUIN_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM df",
    "dataset_name": PENGUIN_DATASET,
    "epsilon": SMARTNOISE_QUERY_EPSILON,
    "delta": SMARTNOISE_QUERY_DELTA,
    "mechanisms": {"count": "gaussian"},
    "postprocess": True,
}

example_dummy_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM df",
    "dataset_name": PENGUIN_DATASET,
    "epsilon": DUMMY_EPSILON,
    "delta": DUMMY_DELTA,
    "mechanisms": {"count": "gaussian"},
    "postprocess": False,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql_cost = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM df",
    "dataset_name": PENGUIN_DATASET,
    "epsilon": SMARTNOISE_QUERY_EPSILON,
    "delta": SMARTNOISE_QUERY_DELTA,
    "mechanisms": {"count": "gaussian"},
}

MEASUREMENT_PIPELINE = (
    '{"version": "0.10.0a20240722001", '
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
    "opendp_json": MEASUREMENT_PIPELINE,
    "pipeline_type": "legacy",  # TODO set constant
    "delta": 1e-6,
    "mechanism": None,
    "output_measure_type_arg": None,
}

example_dummy_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": MEASUREMENT_PIPELINE,
    "pipeline_type": "legacy",  # TODO set constant
    "delta": 1e-6,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
    "mechanism": None,
    "output_measure_type_arg": None,
}

DIFFPRIVLIB_JSON = (
    '{"module": "diffprivlib", '
    '"version": "0.6.4", '
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
    "diffprivlib_json": DIFFPRIVLIB_JSON,
    "feature_columns": [
        "bill_length_mm",
        "bill_depth_mm",
        "flipper_length_mm",
        "body_mass_g",
    ],
    "target_columns": ["species"],
    "test_size": 0.2,
    "test_train_split_seed": 1,
    "imputer_strategy": "drop",
}

example_dummy_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_JSON,
    "feature_columns": [
        "bill_length_mm",
        "bill_depth_mm",
        "flipper_length_mm",
        "body_mass_g",
    ],
    "target_columns": ["species"],
    "test_train_split_seed": 1,
    "test_size": 0.2,
    "imputer_strategy": "drop",
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}


dtypes_income_dataset = {
    "region": "int32",
    "eco_branch": "int32",
    "profession": "int32",
    "education": "int32",
    "age": "int32",
    "sex": "int32",
    "income": "float64"
}

example_opendp_polars = {
    "dataset_name": FSO_INCOME_DATASET,
    "opendp_json": None, # OPENDP_POLARS_JSON,
    "pipeline_type": "polars",  # TODO set constant
    "delta": 1e-6,
    "mechanism": "laplace",
    "output_measure_type_arg": "float",
}