from typing import Dict

from pydantic import JsonValue

from lomas_core.constants import SSynthGanSynthesizer
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


def make_dummy(example_query: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
    """Make dummy example dummy query based on example query."""
    example_query_dummy = dict(example_query)
    example_query_dummy["dummy_nb_rows"] = DUMMY_NB_ROWS
    example_query_dummy["dummy_seed"] = DUMMY_SEED
    return example_query_dummy


# Lomas logic
# -----------------------------------------------------------------------------

example_get_admin_db_data: Dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
}

example_get_dummy_dataset: Dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
    "dummy_nb_rows": DUMMY_NB_ROWS,
    "dummy_seed": DUMMY_SEED,
}

# Smartnoise-SQL
# -----------------------------------------------------------------------------

example_smartnoise_sql_cost: Dict[str, JsonValue] = {
    "query_str": SQL_QUERY,
    "dataset_name": PENGUIN_DATASET,
    "epsilon": QUERY_EPSILON,
    "delta": QUERY_DELTA,
    "mechanisms": DP_MECHANISM,
}

example_smartnoise_sql: Dict[str, JsonValue] = dict(example_smartnoise_sql_cost)
example_smartnoise_sql["postprocess"] = True

example_dummy_smartnoise_sql: Dict[str, JsonValue] = make_dummy(example_smartnoise_sql)

# Smartnoise-Synth
# -----------------------------------------------------------------------------

example_smartnoise_synth_cost: Dict[str, JsonValue] = {
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
example_smartnoise_synth_query: Dict[str, JsonValue] = dict(example_smartnoise_synth_cost)
example_smartnoise_synth_query["return_model"] = True
example_smartnoise_synth_query["condition"] = ""
example_smartnoise_synth_query["nb_samples"] = SNSYNTH_NB_SAMPLES

example_dummy_smartnoise_synth_query: Dict[str, JsonValue] = make_dummy(example_smartnoise_synth_query)

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

example_opendp: Dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
    "opendp_json": OPENDP_PIPELINE,
    "fixed_delta": QUERY_DELTA,
}
example_dummy_opendp: Dict[str, JsonValue] = make_dummy(example_opendp)

# OpenDP Polars
# -----------------------------------------------------------------------------
OPENDP_POLARS_PIPELINE: str = (
    '{"DataFrameScan":{"df":{"columns":[{"name":"region","datatype":"Int32",'
    '"bit_settings":"","values":[6,5,4,2,3,1,1,1,2,6]},{"name":"eco_branch",'
    '"datatype":"Int32","bit_settings":"","values":[66,90,55,63,94,73,65,59,'
    '60,92]},{"name":"profession","datatype":"Int32","bit_settings":"","values":'
    '[32,81,71,10,42,91,53,10,74,73]},{"name":"education","datatype":"Int32",'
    '"bit_settings":"","values":[7,2,1,7,1,5,1,3,4,4]},{"name":"age","datatype":'
    '"Int32","bit_settings":"","values":[36,19,18,23,18,49,42,48,30,46]},{"name":'
    '"sex","datatype":"Int32","bit_settings":"","values":[2,1,1,2,2,2,1,2,2,2]},'
    '{"name":"income","datatype":"Float64","bit_settings":"","values":[69156.22632'
    "652307,39503.22097393128,14374.55399721871,72427.3456792141,53010.07792509686,"
    "31713.94568033661,49097.70052434712,89059.29560055102,93470.30807966871,36421."
    '72447419795]}]},"schema":{"inner":{"region":"Int32","eco_branch":"Int32",'
    '"profession":"Int32","education":"Int32","age":"Int32","sex":"Int32","income":'
    '"Float64"}},"output_schema":null,"filter":null}}'
)

OPENDP_POLARS_PIPELINE_COVID: str = (
    '{"DataFrameScan":{"df":{"columns":[{"name":"patient_id","datatype":"Int32",'
    '"bit_settings":"","values":[7013,2739]},{"name":"id","datatype":"Int32",'
    '"bit_settings":"","values":[1023,540]},{"name":"date","datatype":"String",'
    '"bit_settings":"","values":["t","c"]},{"name":"temporal","datatype":"Int32",'
    '"bit_settings":"","values":[4,1]},{"name":"georegion","datatype":"String",'
    '"bit_settings":"","values":["BS","VS"]},'
    '{"name":"agegroup","datatype":"String",'
    '"bit_settings":"","values":["70 - 79","unknown"]},'
    '{"name":"sex","datatype":"String",'
    '"bit_settings":"","values":["other","other"]},'
    '{"name":"testType","datatype":"String",'
    '"bit_settings":"","values":["rapid_antigen_test",'
    '"rapid_antigen_test"]},{"name":"testResult",'
    '"datatype":"String","bit_settings":"",'
    '"values":["other","other"]},{"name":"country",'
    '"datatype":"String","bit_settings":"","values":["other","unknown"]},'
    '{"name":"subType","datatype":"String",'
    '"bit_settings":"","values":["BA.2.75","XBB"]},'
    '{"name":"hospitalization","datatype":"Boolean","bit_settings":"",'
    '"values":[false,true]},{"name":"death","datatype":"Boolean","bit_settings":"",'
    '"values":[true,false]}]},"schema":{"inner":{"patient_id":"Int32","id":"Int32",'
    '"date":"String","temporal":"Int32","georegion":"String","agegroup":"String",'
    '"sex":"String","testType":"String","testResult":"String","country":"String",'
    '"subType":"String","hospitalization":"Boolean","death":"Boolean"}},'
    '"output_schema":null,"filter":null}}'
)

example_opendp_polars: Dict[str, JsonValue] = {
    "dataset_name": FSO_INCOME_DATASET,
    "opendp_json": OPENDP_POLARS_PIPELINE,
    "pipeline_type": "polars",  # TODO set constant
    "delta": QUERY_DELTA,
    "mechanism": "laplace",
}

example_opendp_polars_datetime: Dict[str, JsonValue] = {
    "dataset_name": COVID_DATASET,
    "opendp_json": OPENDP_POLARS_PIPELINE_COVID,
    "pipeline_type": "polars",  # TODO set constant
    "delta": QUERY_DELTA,
    "mechanism": "laplace",
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

example_diffprivlib: Dict[str, JsonValue] = {
    "dataset_name": PENGUIN_DATASET,
    "diffprivlib_json": DIFFPRIVLIB_PIPELINE,
    "feature_columns": FEATURE_COLUMNS,
    "target_columns": TARGET_COLUMNS,
    "test_size": TEST_SIZE,
    "test_train_split_seed": SPLIT_SEED,
    "imputer_strategy": IMPUTER_STRATEGY,
}
example_dummy_diffprivlib: Dict[str, JsonValue] = make_dummy(example_diffprivlib)
