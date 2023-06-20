from utils.constants import (
    DUMMY_EPSILON,
    DUMMY_DELTA,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    IRIS_DATASET,
)

example_diffprivlib = {
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
                    "_items": [
                        [
                            17,
                            1,
                            0,
                            0,
                            1,
                        ],
                        [
                            90,
                            160,
                            10000,
                            4356,
                            99,
                        ],
                    ],
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


example_opendp = {
    "version": "0.6.1",
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

example_get_dataset_metadata = {
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
}

example_dummy_smartnoise_sql = {
    "query_str": "SELECT COUNT(*) AS NB_ROW FROM Schema.Table",
    "dataset_name": IRIS_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
    "epsilon": DUMMY_EPSILON,
    "delta": DUMMY_DELTA,
}

example_mongodb_get_current_budget = {
    "user_name": "Alice",
    "dataset_name": IRIS_DATASET,
}

example_mongodb_get_max_budget = {
    "user_name": "Alice",
    "dataset_name": IRIS_DATASET,
}

