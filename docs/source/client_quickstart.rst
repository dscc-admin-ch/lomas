Quickstart
==========

This is the quickstart guide for Lomas-client, providing initial setup and usage instructions.

Client
------

Installation
~~~~~~~~~~~~

To install lomas-client, follow these steps:

1. Open a terminal.
2. Run the following command:

.. code-block:: bash

    pip install lomas-client

3. You're all set!

First steps
~~~~~~~~~~~~

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