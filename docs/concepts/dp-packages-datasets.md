# Adding a DP package or a Dataset Connector to Lomas

## Adding a DP package

Lomas is built on top of existing Python DP packages. Follow these steps to add a new package, let's call it 'NewLibrary':

0. Run `uv add <new-package>` in the core directory to add the package as a dependency.
1. Add the library the the `DPLibraries` StrEnum class in `core/lomas_core/constants.py` (`DPLibraries.NEW_LIBRARY = "new_library"`) and add the `NewLibraryQuerier` to the worker code.
2. Create a file for your querier in the folder `server/lomas_server/dp_queries/dp_libraries/new_library.py`. Inside, create a class `NewLibraryQuerier` that inherits from `DPQuerier` (`lomas/lomas_server/dp_queries/dp_querier.py`), your class must contain a `cost` method that return the cost of a query and a `query` method that return a result of a DP query.
3. Add the three associated API endpoints .
    - a. Add the endpoint handlers in `server/lomas_server/routes/routes_dp.py`: `/new_library_query` (for queries on the real dataset), `/dummy_new_library_query` (for queries on the dummy dataset) and `/estimate_new_library_cost` (for estimating the privacy budget cost of a query).
    - b. The endpoints should have predefined pydantic BaselModel types. Add BaseModel classes of expected input `NewLibraryModel`, `DummyNewLibraryModel`, `NewLibraryCostModel` in  `server/lomas_server/utils/query_models.py` and add the request case in the function `model_input_to_lib()`.
    - c. The endpoints should have predefined default values `example_new_library`, `example_dummy_new_library` in  `server/lomas_server/utils/query_examples.py`.
4. Add tests in `server/lomas_server/tests/test_new_library.py` to test all functionnalities and options of the new library.
5. Add the associated method in `lomas-client` library in `client/lomas_client/client.py`. In this case there should be `new_library_query` for queries on the private and on the dummy datasets and `estimate_new_library_cost` to estimate the cost of a query.
6. Add a notebook `Demo_Client_Notebook_NewLibrary.ipynb` in `client/notebook/` to give example of the use of the library.

### External Loggers
Some packages have 'custom object' parameters which are not readily serializable.
In those cases, a `logger` library can be made to serialise the object in the client (before sending them to the server via FastAPI) and then deserialise them in their `DPQuerier` class in the server.

Some examples are avalaible here:
- `diffprivlib_logger` for diffprivlib pipelines: https://github.com/dscc-admin-ch/diffprivlib-logger

Do not forget to add these packages as dependencies to the Lomas core package.

## Adding a Data Connector (for private dataset in various databases)
Here is the explanation of how to add a new data connector named `NewDataConnector` for the example.

1. Add the new dataset store to the lomas core collection models in `core/lomas_core/models/collections.py` with the proper discriminator.
2. Create a file for your dataset store in the folder `server/lomas_server/data_connector/new_data_connector.py`. Inside, create a class `NewDataConnector` that inherits from `DataConnector` (`server/lomas_server/data_connector/data_connector.py`), your class must contain a `get_pandas_df` method that return a dataframe of the dataset.
3. Expand the type adapter in `server/lomas_server/data_connector/__init__.py`.
4. Add tests in `server/lomas_server/tests/` to test all functionnalities of the new data connector.
