# just an example script for WIP

from opendp.mod import enable_features
enable_features('contrib')
import opendp_logger.trans as trans
income_preprocessor = (
    # Convert data into a dataframe where columns are of type Vec<str>
    trans.make_split_dataframe(separator=",", col_names=["hello", "world"]) >>
    # Selects a column of df, Vec<str>
    trans.make_select_column(key="income", TOA=str)
)

# the ast object maintained in the pipeline
# print("ast:", income_preprocessor.ast)

# the ast to json
json_obj = income_preprocessor.to_json()
print("json:", json_obj)

from opendp_logger.constructor import opendp_constructor

# reconstruct the obj from the json string
test = opendp_constructor(json_obj, ptype="json")

print(test)