from base64 import b64encode

import opendp.prelude as dp  # noqa: F401
import polars as pl
from pydantic import JsonValue

from lomas_core.constants import (
    OpenDpMechanism,
    OpenDpPipelineType,
    SSynthGanSynthesizer,
)
from lomas_core.models.constants import (
    DIFFPRIVLIB_VERSION,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    OPENDP_VERSION,
)

# Query constants
PENGUIN_DATASET: str = "PENGUIN"
FSO_INCOME_DATASET: str = "FSO_INCOME_SYNTHETIC"
COVID_DATASET: str = "COVID_SYNTHETIC"
QUERY_EPSILON: float = 0.1
QUERY_DELTA: float = 0.00001
SQL_QUERY: str = "SELECT COUNT(*) AS NB_ROW FROM df"
DP_MECHANISM: JsonValue = {"count": "gaussian"}
FEATURE_COLUMNS: JsonValue = [
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
]
TARGET_COLUMNS: JsonValue = ["species"]
SPLIT_SEED: int = 4
TEST_SIZE: float = 0.2
IMPUTER_STRATEGY: str = "drop"
SNSYNTH_NB_SAMPLES: int = 200


def make_dummy(example_query: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Make dummy example dummy query based on example query."""
    example_query_dummy = dict(example_query)
    example_query_dummy["dummy_nb_rows"] = DUMMY_NB_ROWS
    example_query_dummy["dummy_seed"] = DUMMY_SEED
    return example_query_dummy


# Lomas logic
# -----------------------------------------------------------------------------

example_get_admin_db_data: dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
}

example_get_dummy_dataset: dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

# Smartnoise-SQL
# -----------------------------------------------------------------------------

example_smartnoise_sql_cost: dict[str, JsonValue] = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "mechanisms": DP_MECHANISM,
}

example_smartnoise_sql: dict[str, JsonValue] = dict(example_smartnoise_sql_cost)
example_smartnoise_sql["postprocess"] = True

example_dummy_smartnoise_sql: dict[str, JsonValue] = make_dummy(example_smartnoise_sql)

# Smartnoise-Synth
# -----------------------------------------------------------------------------

example_smartnoise_synth_cost: dict[str, JsonValue] = {
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
example_smartnoise_synth_query: dict[str, JsonValue] = dict(example_smartnoise_synth_cost)
example_smartnoise_synth_query["return_model"] = True
example_smartnoise_synth_query["condition"] = ""
example_smartnoise_synth_query["nb_samples"] = SNSYNTH_NB_SAMPLES

example_dummy_smartnoise_synth_query: dict[str, JsonValue] = make_dummy(example_smartnoise_synth_query)

# OpenDP
# -----------------------------------------------------------------------------

OPENDP_PIPELINE: str = (
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

example_opendp: dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": b64encode(OPENDP_PIPELINE.encode("utf-8")).decode("utf-8"),
    "fixed_delta": QUERY_DELTA,
    "pipeline_type": OpenDpPipelineType.LEGACY,
    "mechanism": None,
}
example_dummy_opendp: dict[str, JsonValue] = make_dummy(example_opendp)

# OpenDP Polars
# -----------------------------------------------------------------------------
OPENDP_POLARS_PIPELINE_DICTS: list[dict] = [
    {
        "region": 1,
        "eco_branch": 85,
        "profession": 52,
        "education": 7,
        "age": 60,
        "sex": 1,
        "income": 23496.63345669291,
    },
    {
        "region": 6,
        "eco_branch": 16,
        "profession": 94,
        "education": 5,
        "age": 44,
        "sex": 0,
        "income": 55903.89391456765,
    },
    {
        "region": 5,
        "eco_branch": 71,
        "profession": 73,
        "education": 2,
        "age": 22,
        "sex": 1,
        "income": 7317.908354313357,
    },
    {
        "region": 4,
        "eco_branch": 25,
        "profession": 74,
        "education": 7,
        "age": 112,
        "sex": 1,
        "income": 82935.48602726562,
    },
    {
        "region": 4,
        "eco_branch": 16,
        "profession": 73,
        "education": 4,
        "age": 94,
        "sex": 0,
        "income": 63534.775513084416,
    },
]

OPENDP_POLARS_PIPELINE: bytes = pl.from_dicts(OPENDP_POLARS_PIPELINE_DICTS).lazy().serialize()

OPENDP_POLARS_PIPELINE_COVID_DICTS: list[dict] = [
    {
        "patient_id": 7013,
        "id": 1023,
        "date": "t",
        "temporal": 4,
        "georegion": "BS",
        "agegroup": "70 - 79",
        "sex": "other",
        "testType": "rapid_antigen_test",
        "testResult": "other",
        "country": "other",
        "subType": "BA.2.75",
        "hospitalization": False,
        "death": True,
    },
    {
        "patient_id": 2739,
        "id": 540,
        "date": "c",
        "temporal": 1,
        "georegion": "VS",
        "agegroup": "unknown",
        "sex": "other",
        "testType": "rapid_antigen_test",
        "testResult": "other",
        "country": "unknown",
        "subType": "XBB",
        "hospitalization": True,
        "death": False,
    },
]

OPENDP_POLARS_PIPELINE_COVID: bytes = pl.from_dicts(OPENDP_POLARS_PIPELINE_COVID_DICTS).lazy().serialize()

example_opendp_polars: dict[str, JsonValue] = {
    "dataset_name": FSO_INCOME_DATASET,
    "opendp_json": b64encode(OPENDP_POLARS_PIPELINE).decode("utf-8"),
    "pipeline_type": OpenDpPipelineType.POLARS,
    "fixed_delta": QUERY_DELTA,
    "mechanism": OpenDpMechanism.LAPLACE,
}


example_opendp_polars_plan = {**example_opendp_polars}
example_opendp_polars_plan["opendp_json"] = b64encode(
    pl.from_dicts(OPENDP_POLARS_PIPELINE_DICTS)
    .lazy()
    .select(pl.col("income").fill_null(0).dp.mean(bounds=(1000, 100000), scale=100_000.0))
    .serialize()
).decode("utf-8")

example_opendp_polars_datetime: dict[str, JsonValue] = {
    "dataset_name": COVID_DATASET,
    "opendp_json": b64encode(OPENDP_POLARS_PIPELINE_COVID).decode("utf-8"),
    "pipeline_type": OpenDpPipelineType.POLARS,
    "fixed_delta": QUERY_DELTA,
    "mechanism": OpenDpMechanism.LAPLACE,
}


# DiffPrivLib
# -----------------------------------------------------------------------------

DIFFPRIVLIB_PIPELINE: str = (
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

example_diffprivlib: dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_PIPELINE,
    "feature_columns": FEATURE_COLUMNS,
    "target_columns": TARGET_COLUMNS,
    "test_size": TEST_SIZE,
    "test_train_split_seed": SPLIT_SEED,
    "imputer_strategy": IMPUTER_STRATEGY,
}
example_dummy_diffprivlib: dict[str, JsonValue] = make_dummy(example_diffprivlib)
