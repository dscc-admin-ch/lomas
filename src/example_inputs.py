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
              1
            ],
            [
              90,
              160,
              10000,
              4356,
              99
            ]
          ]
        },
        "accountant": "_dpl_instance:BudgetAccountant"
      }
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
        "accountant": "_dpl_instance:BudgetAccountant"
      }
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
        "accountant": "_dpl_instance:BudgetAccountant"
      }
    }
  ]
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

example_smartnoise_sql = {
  "query_str": "SELECT COUNT(col2) FROM comp.comp GROUP BY col1",
  "epsilon": 10,
  "delta": 0
}

example_smartnoise_synth = {
  "model": "MWEM",
  "epsilon": 1,

}