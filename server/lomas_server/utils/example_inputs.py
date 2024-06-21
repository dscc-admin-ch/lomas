# Dummy queries
DUMMY_EPSILON = 100.0
DUMMY_DELTA = 0.99

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

# DUMMY dataset name
PENGUIN_DATASET = "PENGUIN"
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
    '{"version": "0.8.0", '
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
    "fixed_delta": 1e-6,
}

example_dummy_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": MEASUREMENT_PIPELINE,
    "fixed_delta": 1e-6,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

diffprivlib_json = {
    "module": "diffprivlib",
    "version": "0.6.0",
    "pipeline": [
        {
            "type": "_dpl_type:StandardScaler",
            "name": "scaler",
            "params": {
                "with_mean": True,
                "with_std": True,
                "copy": True,
                "epsilon": 1,
                "bounds": {
                    "_tuple": True,
                    "_items": [[17, 1, 0, 0, 1], [90, 160, 10000, 4356, 99]],
                },
                "accountant": "_dpl_instance:BudgetAccountant",
            },
        },
        {
            "type": "_dpl_type:PCA",
            "name": "pca",
            "params": {
                "n_components": 2,
                "copy": True,
                "whiten": False,
                "random_state": None,
                "centered": True,
                "epsilon": 1,
                "data_norm": 5,
                "bounds": None,
                "accountant": "_dpl_instance:BudgetAccountant",
            },
        },
        {
            "type": "_dpl_type:LogisticRegression",
            "name": "lr",
            "params": {
                "tol": 0.0001,
                "C": 1,
                "fit_intercept": True,
                "max_iter": 100,
                "verbose": 0,
                "warm_start": False,
                "n_jobs": None,
                "epsilon": 1,
                "data_norm": 5,
                "accountant": "_dpl_instance:BudgetAccountant",
            },
        },
    ],
}

example_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": diffprivlib_json,
    "feature_columns": ["species", "bill_depth_mm"],
    "target_columns": ["bill_length_mm"],
    "test_size": 0.2,
    "test_train_split_seed": 1,
    "imputer_strategy": "mean",
}

example_dummy_diffprivlib = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": diffprivlib_json,
    "feature_columns": ["species", "bill_depth_mm"],
    "target_columns": ["bill_length_mm"],
    "test_train_split_seed": 1,
    "test_size": 0.2,
    "imputer_strategy": "mean",
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}
