# DSCC SDD Client

The `dscc_sdd_client` library is a client to interact with the DSCC SDD server.

Utilizing this client library is strongly advised for querying and interacting with the server, as it takes care of all the necessary tasks such as serialization, deserialization, REST API calls, and ensures the correct installation of other required libraries.

### Installation
It can be installed with the command:
```python
pip install dscc_sdd_client
```

### Examples
To see detailed examples of the library, many notebooks are available  in the [client](https://github.com/dscc-admin/dscc_sdd/blob/develop/client) folder. For instance, refer to [Demo_Client_Notebook.ipynb](https://github.com/dscc-admin/dscc_sdd/blob/develop/client/Demo_Client_Notebook.ipynb).


### More detailed documentation
To see a more detailed documentation, clone the repo go to `dscc_sdd_client/client` and run:

```python
sphinx-build -M html documentation docs
```

To see the pages, go to `dscc_sdd_client/client/docs/html`, run:

```
start .\index.html
```
(in windows) and the doc page will open!