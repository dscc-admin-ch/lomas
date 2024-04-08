# Dummy queries
DUMMY_EPSILON = 1e32 * 1.0
DUMMY_DELTA = 1.0

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

# DUMMY dataset name
IRIS_DATASET = "IRIS"


example_get_db_data = {
    "dataset_name": IRIS_DATASET,
}

example_get_dummy_dataset = {
    "dataset_name": IRIS_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": IRIS_DATASET,
    "epsilon": 0.1,
    "delta": 0.00001,
    "mechanisms": {"count": "discrete_gaussian"},
    "postprocess": True,
}

example_dummy_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": IRIS_DATASET,
    "epsilon": DUMMY_EPSILON,
    "delta": DUMMY_DELTA,
    "mechanisms": {"count": "discrete_gaussian"},
    "postprocess": False,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

example_smartnoise_sql_cost = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": IRIS_DATASET,
    "epsilon": 0.1,
    "delta": 0.00001,
    "mechanisms": {"count": "discrete_gaussian"},
}

opendp_json = {
    "version": "0.8.0",
    "ast": {
        "func": "make_chain_tt",
        "module": "comb",
        "type": "Transformation",
        "args": [
            {
                "func": "make_select_column",
                "module": "trans",
                "type": "Transformation",
                "args": [],
                "kwargs": {
                    "key": "income",
                    "TOA": "py_type:str",
                },
            },
            {
                "func": "make_split_dataframe",
                "module": "trans",
                "type": "Transformation",
                "args": [],
                "kwargs": {
                    "separator": ",",
                    "col_names": [
                        "hello",
                        "world",
                    ],
                },
            },
        ],
        "kwargs": {},
    },
}

example_opendp = {
    "dataset_name": IRIS_DATASET,
    "opendp_json": opendp_json,
    "input_data_type": "df",
}

example_dummy_opendp = {
    "dataset_name": IRIS_DATASET,
    "opendp_json": opendp_json,
    "input_data_type": "df",
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

# example_diffprivlib_cost = {
#     "dataset_name": IRIS_DATASET,
#     "diffprivlib_json": diffprivlib_json,
#     "feature_columns": ["sepal_width", "petal_length"],
#     "target_columns": ["sepal_length"],
# }

example_diffprivlib = {
    "dataset_name": IRIS_DATASET,
    "diffprivlib_json": diffprivlib_json,
    "feature_columns": ["sepal_width", "petal_length"],
    "target_columns": ["sepal_length"],
    "test_size": 0.2,
    "test_train_split_seed": 1,
    "imputer_strategy": "mean",
}

example_dummy_diffprivlib = {
    "dataset_name": IRIS_DATASET,
    "diffprivlib_json": diffprivlib_json,
    "feature_columns": ["sepal_width", "petal_length"],
    "target_columns": ["sepal_length"],
    "test_train_split_seed": 1,
    "test_size": 0.2,
    "imputer_strategy": "mean",
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED
}
