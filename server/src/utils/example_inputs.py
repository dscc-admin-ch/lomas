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

example_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": {
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
    },
    "input_data_type": "df",
    "fixed_delta": 1e-6,
}

example_dummy_opendp = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": {
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
    },
    "input_data_type": "df",
    "fixed_delta": 1e-6,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}
