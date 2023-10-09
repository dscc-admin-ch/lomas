from fso_sdd_demo.client.diffprivlib import serialize_pipeline

from sklearn.pipeline import Pipeline
from diffprivlib import models


def test_serialize_deserialize():
    example_pipe = Pipeline(
        [
            (
                "scaler",
                models.StandardScaler(
                    bounds=([17, 1, 0, 0, 1], [90, 160, 10000, 4356, 99])
                ),
            ),
            ("pca", models.PCA(2, data_norm=5, centered=True)),
            ("lr", models.LogisticRegression(data_norm=5)),
        ]
    )

    example_expected_json = """{"module": "diffprivlib", "version": "0.6.0", "pipeline": [{"type": "_dpl_type:StandardScaler", "name": "scaler", "params": {"with_mean": true, "with_std": true, "copy": true, "epsilon": 1.0, "bounds": {"_tuple": true, "_items": [[17, 1, 0, 0, 1], [90, 160, 10000, 4356, 99]]}, "random_state": null, "accountant": "_dpl_instance:BudgetAccountant"}}, {"type": "_dpl_type:PCA", "name": "pca", "params": {"n_components": 2, "copy": true, "whiten": false, "random_state": null, "centered": true, "epsilon": 1.0, "data_norm": 5, "bounds": null, "accountant": "_dpl_instance:BudgetAccountant"}}, {"type": "_dpl_type:LogisticRegression", "name": "lr", "params": {"tol": 0.0001, "C": 1.0, "fit_intercept": true, "random_state": null, "max_iter": 100, "verbose": 0, "warm_start": false, "n_jobs": null, "epsilon": 1.0, "data_norm": 5, "accountant": "_dpl_instance:BudgetAccountant"}}]}"""
    json_str = serialize_pipeline(example_pipe)

    assert json_str == example_expected_json
