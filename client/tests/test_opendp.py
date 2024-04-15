import opendp.transformations as trans
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json

enable_logging()
enable_features("contrib")


def test_serialize() -> None:
    # Random pipeline of transformation
    pipeline = (
        # Convert data into a dataframe where columns are of type Vec<str>
        trans.make_split_dataframe(separator=",", col_names=["hello", "world"])
        >>
        # Selects a column of df, Vec<str>
        trans.make_select_column(key="income", TOA=str)
    )

    # Ast to json to be sent
    json_obj = pipeline.to_json()

    expected_json = (
        '{"version": "0.8.0", '
        '"ast": {'
        '"_type": "constructor", '
        '"func": "make_chain_tt", '
        '"module": "combinators", '
        '"args": ['
        "{"
        '"_type": "constructor", '
        '"func": "make_select_column", '
        '"module": "transformations", '
        '"kwargs": {"key": "income", "TOA": "String"}'
        "}, "
        "{"
        '"_type": "constructor", '
        '"func": "make_split_dataframe", '
        '"module": "transformations", '
        '"kwargs": {"separator": ",", "col_names": {'
        '"_type": "list", '
        '"_items": ["hello", "world"]'
        "}}"
        "}"
        "]"
        "}"
        "}"
    )

    # Assert expected value
    assert json_obj == expected_json


def test_deserialize() -> None:
    pipeline_json = (
        '{"version": "0.8.0", '
        '"ast": {'
        '"_type": "constructor", '
        '"func": "make_chain_tt", '
        '"module": "combinators", '
        '"args": ['
        "{"
        '"_type": "constructor", '
        '"func": "make_select_column", '
        '"module": "transformations", '
        '"kwargs": {"key": "income", "TOA": "String"}'
        "}, "
        "{"
        '"_type": "constructor", '
        '"func": "make_split_dataframe", '
        '"module": "transformations", '
        '"kwargs": {"separator": ",", "col_names": {'
        '"_type": "list", '
        '"_items": ["hello", "world"]'
        "}}"
        "}"
        "]"
        "}"
        "}"
    )

    pipeline = make_load_json(pipeline_json)

    expected_pipeline = (
        # Convert data into a dataframe where columns are of type Vec<str>
        trans.make_split_dataframe(separator=",", col_names=["hello", "world"])
        >>
        # Selects a column of df, Vec<str>
        trans.make_select_column(key="income", TOA=str)
    )

    # Assert expected value
    assert str(pipeline) == str(expected_pipeline)
