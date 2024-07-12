[![PyPi version](https://img.shields.io/pypi/v/lomas_client.svg)](https://pypi.org/project/lomas_client/)
[![PyPi status](https://img.shields.io/pypi/status/lomas_client.svg)](https://pypi.org/project/lomas_client/)

<h1 align="center">
<img src="https://github.com/dscc-admin-ch/lomas/blob/develop/images/lomas_logo_txt.png?raw=true" width="300">
</h1><br>

# Lomas Client

The `lomas_client` library is a client to interact with the Lomas server.

Utilizing this client library is strongly advised for querying and interacting with the server, as it takes care of all the necessary tasks such as serialization, deserialization, REST API calls, and ensures the correct installation of other required libraries. In short, it enables a seamless interaction with the server.

### Installation
It can be installed with the command:
```python
pip install lomas_client
```

### Simple introduction to clien use

#### Creat Client object:
Once the library is installed, a Client object must be created. To create the client, the user needs to give it a few parameters:
- a url: the root application endpoint to the remote secure server.
- a user_name: her name as registered in the database (Emilie)
- a dataset_name: the name of the dataset that she wants to query (PENGUIN)

```python
from lomas_client.client.client import Client
client = Client(url="http://lomas_server_dev:80", user_name = "Emilie", dataset_name = "PENGUIN")
```
Once `client` is initialized it can be used to send requests to respective DP frameworks.

#### Get metadata
Metadata information aout the dataset can be accessed in a format based on SmartnoiseSQL dictionary format, where among other, there is information about all the available columns, their type, bound values (see Smartnoise page for more details). Any metadata is required for Smartnoise-SQL is also required here and additional information such that the different categories in a string type column column can be added.

```python
metadata = client.get_dataset_metadata()
```

#### Get a dummy dataset
Based on the public metadata of the dataset, a random dataframe can be created. By default, there will be 100 rows and the seed is set to 42 to ensure reproducibility, but these 2 variables can be changed to obtain different dummy datasets.
Getting a dummy dataset does not affect the budget as there is no differential privacy here. It is not a synthetic dataset and all that could be learn here is already present in the public metadata (it is created randomly on the fly based on the metadata).

```python
df_dummy = client.get_dummy_dataset(nb_rows = 200, seed = 1)
```

####  Query smartnoise-sql
She can query on the sensitive dataset using smartnoise-sql library in the back-end with the following method:
```python
response = client.smartnoise_query(
    query = ""SELECT COUNT(*) AS nb_penguins FROM df"",  
    epsilon = 0.1, 
    delta = 0.00001,
    dummy = False # Optionnal
)
```
To query on a dummy dataset for testing purposes she can set the dummy flag to True (see notebooks or white paper for further explanations).
NOTE: the 'FROM' of the SQL query must be followed by 'df' for the command to work.

####  Get smartnoise-sql query cost
In SmartnoiseSQL, the budget that will by used by a query might be different than what is asked by the user. The estimate cost function returns the estimated real cost of any query.
```python
real_cost_epsilon, real_cost_delta = client.estimate_smartnoise_cost(
    query = "SELECT COUNT(*) AS nb_penguins FROM df", 
    epsilon = 0.1, 
    delta = 0.000001
)
```
Usually real_cost_epsilon > input_epsilon and real_cost_delta > delta.
NOTE: the 'FROM' of the SQL query must be followed by 'df' for the command to work.


#### Query opendp
She can query on the sensitive dataset using opendp library in the back-end with the following method:
```python
import opendp as dp
import opendp.transformations as trans
import opendp.measurements as meas

pipeline = (
    trans.make_split_dataframe(separator=",", col_names=columns) >>
    trans.make_select_column(key="bill_length_mm", TOA=str) >>
    trans.then_cast_default(TOA=float) >>
    trans.then_clamp(bounds=(bill_length_min, bill_length_max)) >>
    trans.then_resize(size=nb_penguins.tolist(), constant=avg_bill_length) >>
    trans.then_variance() >>
    meas.then_laplace(scale=5.0)
)
result = client.opendp_query(
    opendp_pipeline = pipeline, 
)
```

Similarly as in Smartnoise-sql, to query on a dummy dataset for testing purposes she can set the summy flag to True (see notebooks or white paper for further explanations).

####  Get opendp query cost
The budget that will by used by a query is usually not expressed in the epsilon, delta format used in the server. For instance, in the pipeline exemple above the noise is expressed as `meas.then_laplace(scale=5.0)`. It can be converted in term of the epsilon and delta cost with the function below:
```python
real_cost_epsilon, real_cost_delta = client.estimate_opendp_cost(opendp_pipeline = pipeline)
```


#### Get budget information
There are various functions for the user to track her budget:
- get\_initial\_budget() retrieves the initial budget that was allocated to her by the platform administrator.
- get\_total\_spent\_budget() provides the total amount spent from the budget (accumulated from all previous queries).
- get\_remaining\_budget() returns the remaining budget available for future queries. It is the difference between the initial budget and the total spent budget.
Each of these functionalities return two values, one for epsilon and one for delta.

```python
initial_epsilon, initial_delta = client.get_initial_budget()
total_spent_epsilon, total_spent_delta = client.get_total_spent_budget()
remaining_epsilon, remaining_delta = client.get_remaining_budget()
```


#### Get archives
All queries that are made on the sensitive data are kept in a secure database. With a function call she can see her queries, budget spent and associated responses.

```python
previous_queries = client.get_previous_queries()
```


### Examples
To see detailed examples of the library, many notebooks are available  in the [client](https://github.com/dscc-admin-ch/lomas/tree/master/client/notebooks) folder. For instance, refer to [Demo_Client_Notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/client/notebooks/Demo_Client_Notebook.ipynb).


### More detailed documentation
More detailed documentation is available on [this GitHub Page](https://dscc-admin-ch.github.io/lomas-docs/). 