example_diffprivlib = {
    "pipeline": [
        {
            "name": "scaler",
            "model": "StandardScaler",
            "epsilon": 0.1,
            "args": [],
            "kwargs": {
                "bounds:py_type:tuple": [[17, 1, 0, 0, 1], [90, 160, 10000, 4356, 99]],
                "epsilon": 2,
            },
        },
        {
            "name": "pca",
            "model": "PCA",
            "args": [2],
            "kwargs": {"data_norm": 5, "centered": True, "epsilon": 2},
        },
        {
            "name": "lr",
            "model": "LogisticRegression",
            "args": [],
            "kwargs": {"data_norm": 5, "epsilon": 1},
        },
    ],
    "version": "0.5.2",
}


example_opendp = {
    "version": "0.3.0",
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
                "kwargs": {"key": "income", "TOA": "py_type:str"},
            },
            {
                "func": "make_split_dataframe",
                "module": "trans",
                "type": "Transformation",
                "args": [],
                "kwargs": {"separator": ",", "col_names": ["hello", "world"]},
            },
        ],
        "kwargs": {},
    },
}

example_opendp_str = {
    "\"version\":\"0.3.0\",\"ast\":{\"func\":\"make_chain_tt\",\"module\":\"comb\",\"type\":\"Transformation\",\"args\":[{\"func\":\"make_select_column\",\"module\":\"trans\",\"type\":\"Transformation\",\"args\":[],\"kwargs\":{\"key\":\"income\",\"TOA\":\"py_type:str\"},},{\"func\":\"make_split_dataframe\",\"module\":\"trans\",\"type\":\"Transformation\",\"args\":[],\"kwargs\":{\"separator\":\",\",\"col_names\":[\"hello\",\"world\"]},},],\"kwargs\":{},},"
}