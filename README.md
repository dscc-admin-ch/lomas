# DP Serializers Client
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)](https://www.python.org/)


# Client package for DP Serializer

The dp-seriel-client enables serialization of popular Differential Privacy frameworks.
The client in dp-serializers-client makes it possible to serialize and query data with a corresponding server running.


## Creating Client:
```python
from dp_serial.client.client import Client
dp_client = Client("http://localhost:3031")
```
Once `dp_client` is initialized it can be used to send requests to respective DP frameworks.

## Querying OpenDP
```python
import dp_serial.opendp_logger.trans as trans
import dp_serial.opendp_logger.meas as meas
import dp_serial.opendp_logger.comb as comb

pipeline = comb.make_pureDP_to_fixed_approxDP(
    trans.make_split_dataframe(separator=",", col_names=["col_1", "col_2", "col_3"]) >>
    trans.make_select_column(key="key_name", TOA=str) >>
    trans.make_cast(TIA=str, TOA=int) >>
    trans.make_impute_constant(0) >> 
    trans.make_clamp(bounds=(0, 1)) >>
    trans.make_bounded_sum((0, 1)) >>
    meas.make_base_discrete_laplace(scale=1.)
)

opendp_result = dp_client.opendp(pipeline)

#Data from API server with DP applied
print(opendp_result)
```

## Querying Diffprivlib
```python
from sklearn.pipeline import Pipeline
from diffprivlib import models

#Diffprivlib LR Pipeline 
lr_pipe = Pipeline([
    ('lr', models.LogisticRegression(data_norm=5))
])
#Trained model from API Server with DP applied
trained_model = dp_client.diffprivlib(splr_pipe, y_column="y_return") 
```

## Querying Smartnoise-Synth
```python
cols_to_select = ["col_1", "col_2", "col_3"]
mat = numpy.array([[0.001,0.1,0.001], [0.01,0.1,0.02], [0.41,0.1,0.3]])

mwem_synthetic_data = dp_client.synth("MWEM", 1, 0.0001, select_cols=cols_to_select, mul_matrix=mat)

#Synthetic Data from API server
print(mwem_synthetic_data)
```

## Querying Smartnoise-SQL

```python
query_result = dp_client.sql(
    "SELECT col_1, COUNT(col_2) as ret_col_2 FROM comp.comp GROUP BY col_3", 1,0.0001
)

#Resulting data from APIs with DP applied
print(query_result)
```
