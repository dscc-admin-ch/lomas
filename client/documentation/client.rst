Client
======

To use FSO lomas client, you can do the following:

1. Import the library in your Python code.
2. Initialise the client with required url, name and dataset.
3. You can now use any function as long as you have access to the dataset!

   .. code-block:: python

    # Step 1
    from lomas_client import Client

    # Step 2
    APP_URL = "your_deployement_url"
    USER_NAME = "your_name"
    DATASET_NAME = "name_of_dataset_you_want_to_query"
    client = Client(url=APP_URL, user_name = USER_NAME, dataset_name = DATASET_NAME)

    # Step 3
    res = client.any_query(parameters)

with `any_query` being one of the function presented below and `parameters` being its associated parameters.

Client functionnalities
=======================

.. _get-dataset-metadata:

get_dataset_metadata
--------------------

This function retrieves metadata for the dataset.

.. code-block:: python

    res = client.get_dataset_metadata()

Parameters:
    None

Returns:
    - `dict`: A dictionary containing dataset metadata.

Explanation:
- Use this function to retrieve metadata information for the dataset.

---

.. _get-dummy-dataset:

get_dummy_dataset
-----------------

This function retrieves a dummy dataset with optional parameters.

.. code-block:: python

    res = client.get_dummy_dataset(nb_rows: int = 100, seed: int = 42)

Parameters:
    - `nb_rows` (int, optional): The number of rows in the dummy dataset (default: 100).
    - `seed` (int, optional): The random seed for generating the dummy dataset (default: 42).

Returns:
    - `pd.DataFrame`: A Pandas DataFrame representing the dummy dataset.

Explanation:
- Use this function to retrieve a dummy dataset for testing purposes with optional parameters to customize the dataset.

---

.. _smartnoise-query:

smartnoise_query
----------------

This function executes a SmartNoise query.

.. code-block:: python

    res = client.smartnoise_query(
        query,
        epsilon: float,
        delta: float,
        mechanisms: dict = {},
        postprocess: bool = True,
        dummy: bool = False,
        nb_rows: int = 100,
        seed: int = 42,
    )

Parameters:
    - `query`: The SQL query to execute. NOTE: the table name is `df`, the query must end with "FROM df".
    - `epsilon` (float): Privacy parameter (e.g., 0.1).
    - `delta` (float): Privacy parameter (e.g., 1e-5).
    - `mechanisms` (dict, optional): Dictionary of mechanisms for the query (default: {}). See `Smartnoise-SQL mechanisms documentation <https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms>`_.
    - `postprocess` (bool, optional): Whether to postprocess the query results (default: True). See `Smartnoise-SQL postprocessing documentation <https://docs.smartnoise.org/sql/advanced.html#postprocess>`_.
    - `dummy` (bool, optional): Whether to use a dummy dataset (default: False).
    - `nb_rows` (int, optional): The number of rows in the dummy dataset (default: 100).
    - `seed` (int, optional): The random seed for generating the dummy dataset (default: 42).

Returns:
    - `pd.DataFrame`: A Pandas DataFrame containing the query results.

Explanation:
- Use this function to execute a SmartNoise query with various privacy and data customization options.


# Continue from where the previous example left off...

---

.. _estimate-smartnoise-cost:

estimate_smartnoise_cost
------------------------

This function estimates the cost of executing a SmartNoise query.

.. code-block:: python

    res = client.estimate_smartnoise_cost(
        query,
        epsilon: float,
        delta: float,
        mechanisms: dict = {},
    )

Parameters:
    - `query`: The SQL query to estimate the cost for. NOTE: the table name is `df`, the query must end with "FROM df".
    - `epsilon` (float): Privacy parameter (e.g., 0.1).
    - `delta` (float): Privacy parameter (e.g., 1e-5).
    - `mechanisms` (dict, optional): Dictionary of mechanisms for the query (default: {}). See `Smartnoise-SQL mechanisms documentation <https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms>`_.

Returns:
    - `dict`: A dictionary containing the estimated cost.

Explanation:
- Use this function to estimate the cost of executing a SmartNoise query with specified privacy parameters.

---

.. _opendp-query:

opendp_query
------------

This function executes an OpenDP query.

.. code-block:: python

    res = client.opendp_query(
        opendp_pipeline,
        fixed_delta: float = None,
        dummy: bool = False,
        nb_rows: int = 100,
        seed: int = 42,
    )

Parameters:
    - `opendp_pipeline`: The OpenDP pipeline for the query.
    - `fixed_delta`: If the pipeline measurement is of type "ZeroConcentratedDivergence" (e.g. with `make_gaussian`) then it is converted to "SmoothedMaxDivergence" with `make_zCDP_to_approxDP` (see `opendp measurements documentation <https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP>`_). In that case a `fixed_delta` must be provided by the user.
    - `dummy` (bool, optional): Whether to use a dummy dataset (default: False).
    - `nb_rows` (int, optional): The number of rows in the dummy dataset (default: 100).
    - `seed` (int, optional): The random seed for generating the dummy dataset (default: 42).

Returns:
    - `pd.DataFrame`: A Pandas DataFrame containing the query results.

Explanation:
- Use this function to execute an OpenDP query with options for specifying the input data type and using a dummy dataset.

---

.. _estimate-opendp-cost:

estimate_opendp_cost
--------------------

This function estimates the cost of executing an OpenDP query.

.. code-block:: python

    res = client.estimate_opendp_cost(
        opendp_pipeline,
        fixed_delta: float = None,
    )

Parameters:
    - `opendp_pipeline`: The OpenDP pipeline for the query.

Returns:
    - `dict`: A dictionary containing the estimated cost.

Explanation:
- Use this function to estimate the cost of executing an OpenDP query with options for specifying the input data type.

---

.. _get-initial-budget:

get_initial_budget
------------------

This function retrieves the initial budget.

.. code-block:: python

    res = client.get_initial_budget()

Parameters:
    None

Returns:
    - `dict`: A dictionary containing the initial budget.

Explanation:
- Use this function to retrieve the initial budget.

---

.. _get-total-spent-budget:

get_total_spent_budget
----------------------

This function retrieves the total spent budget.

.. code-block:: python

    res = client.get_total_spent_budget()

Parameters:
    None

Returns:
    - `dict`: A dictionary containing the total spent budget.

Explanation:
- Use this function to retrieve the total spent budget.

---

.. _get-remaining-budget:

get_remaining_budget
--------------------

This function retrieves the remaining budget.

.. code-block:: python

    res = client.get_remaining_budget():

Parameters:
    None

Returns:
    - `dict`: A dictionary containing the remaining budget.

Explanation:
- Use this function to retrieve the remaining budget.


---

.. _get-previous-queris:

get_previous_queries
--------------------

This function retrieves the previous queries of the user.

.. code-block:: python

    res = client.get_previous_queries():

Parameters:
    None

Returns:
    - `list[dict]`: A list of dictionary containing the different queries on the private dataset.

Explanation:
- Use this function to get the list af all the previous queries of the user on the dataset.
