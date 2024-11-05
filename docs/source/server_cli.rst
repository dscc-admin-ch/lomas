CLI
==================

This section provides detailed instructions on how to use the CLI to perform various 
administrative tasks efficiently.


Overview
----------------

The CLI allows data owners to interact with the administrative database directly from the command 
line. It provides functionalities for managing users, datasets, metatada and queries_archive collections within the MongoDB environment.

NOTE: it is possible to use a :doc:`streamlit app <server_dashboard>` to interact with the database instead.

MongoDB Connection
------------------
The CLI requires connection parameters to establish a connection with MongoDB. These parameters must always for provided (for all functions):

- ``-db_u, --username``: MongoDB username (default: "user")
- ``-db_pwd, --password``: MongoDB password (default: "user_pwd")
- ``-db_a, --address``: MongoDB server address (default: "mongodb")
- ``-db_p, --port``: MongoDB server port (default: 27017)
- ``-db_n, --db_name``: MongoDB database name (default: "defaultdb")

MongoDB Administration
----------------------

Users
~~~~~
- ``add_user``: Add a user to the users collection.

  - ``-u, --user``: Username of the user to be added (required).

- ``add_user_with_budget``: Add a user with a budget to the users collection.

  - ``-u, --user``: Username of the user to be added (required).
  - ``-d, --dataset``: Name of the dataset for the user (required).
  - ``-e, --epsilon``: Epsilon value for the dataset (required).
  - ``-del, --delta``: Delta value for the dataset (required).

- ``del_user``: Delete a user from the users collection.

  - ``-u, --user``: Username of the user to be deleted (required).

- ``add_dataset_to_user``: Add a dataset with initialized budget values for a user.

  - ``-u, --user``: Username of the user (required).
  - ``-d, --dataset``: Name of the dataset to be added (required).
  - ``-e, --epsilon``: Epsilon value for the dataset (required).
  - ``-del, --delta``: Delta value for the dataset (required).

- ``del_dataset_to_user``: Delete a dataset for a user from the users collection.

  - ``-u, --user``: Username of the user (required).
  - ``-d, --dataset``: Name of the dataset to be deleted (required).

- ``set_budget_field``: Set a budget field to a given value for a specified user and dataset.

  - ``-u, --user``: Username of the user (required).
  - ``-d, --dataset``: Name of the dataset (required).
  - ``-f, --field``: Field to be set ("initial_epsilon" or "initial_delta") (required).
  - ``-v, --value``: Value to set for the field (required).

- ``set_may_query``: Set the "may query" field to a given value for a specified user.

  - ``-u, --user``: Username of the user (required).
  - ``-v, --value``: Value to set for "may query" (choices: "False" or "True") (required).

- ``get_user``: Show all information about a user in the users collection.

  - ``-u, --user``: Username of the user to be shown (required).

- ``add_users_via_yaml``: Create users collection from a YAML file.

  - ``-yf, --yaml_file``: Path to the YAML file (required).
  - ``-c, --clean``: Clean the existing users collection (optional, default: False).
  - ``-o, --overwrite``: Overwrite the existing users collection (optional, default: False).

- ``get_archives``: Show all previous queries from a user.

  - ``-u, --user``: Username of the user to show archives (required).

- ``get_users``: Get the list of all users in the 'users' collection.

- ``get_user_datasets``: Get the list of all datasets from a user.

  - ``-u, --user``: Username of the user to show datasets (required).

Datasets
~~~~~~~~
- ``add_dataset``: Add a dataset to the datasets collection.

  - ``-d, --dataset_name``: Name of the dataset (required).
  - ``-db, --database_type``: Type of the database where the dataset is stored (required).
  - ``-d_path, --dataset_path``: Path to the dataset (required if database_type is 'PATH_DB').
  - ``-s3b, --bucket``: S3 bucket name for the dataset file (required if database_type is 'S3_DB').
  - ``-s3k, --key``: S3 key for the dataset file  (required if database_type is 'S3_DB').
  - ``-s3_url, --endpoint_url``: S3 endpoint URL for the dataset file  (required if database_type is 'S3_DB').
  - ``-s3_ak, --access_key_id``: AWS access key ID for S3 for the dataset file (required if database_type is 'S3_DB').
  - ``-s3_sak, --secret_access_key``: AWS secret access key for S3 for the dataset file  (required if database_type is 'S3_DB').
  - ``-m_db, --metadata_database_type``: Type of the database where metadata is stored (required).
  - ``-mp, --metadata_path``: Path to the metadata (required if metadata_database_type is 'PATH_DB').
  - ``-m_s3b, --metadata_bucket``: S3 bucket name for metadata (required if metadata_database_type is 'S3_DB').
  - ``-m_s3k, --metadata_key``: S3 key for metadata (required if metadata_database_type is 'S3_DB').
  - ``-m_s3_url, --metadata_endpoint_url``: S3 endpoint URL for metadata (required if metadata_database_type is 'S3_DB').
  - ``-m_s3_ak, --metadata_access_key_id``: AWS access key ID for metadata (required if metadata_database_type is 'S3_DB').
  - ``-m_s3_sak, --metadata_secret_access_key``: AWS secret access key for metadata (required if metadata_database_type is 'S3_DB').

- ``add_datasets_via_yaml``: Create datasets to database type collection based on a yaml file.

  - ``-yf, --yaml_file``: Path to the YAML file (required).
  - ``-c, --clean``: Clean the existing datasets collection (optional, default: False).
  - ``-od, --overwrite_datasets``: Overwrite the existing datasets collection (optional, default: False).
  - ``-om, --overwrite_metadata``: Overwrite the existing metadata collection (optional, default: False).

- ``del_dataset``: Delete dataset and metadata from datasets and metadata collection.

  - ``-d, --dataset``: Name of the dataset to be deleted (required).

- ``get_dataset``: Show a dataset from the dataset collection.

  - ``-d, --dataset``: Name of the dataset to show (required).

- ``get_metadata``: Show metadata from the metadata collection.

  - ``-d, --dataset``: Name of the dataset of the metadata to show (required).

- ``get_datasets``: Get the list of all datasets in the 'datasets' collection.

Collections
~~~~~~~~~~~
- ``drop_collection``: Delete a collection from the database.

  - ``-c, --collection``: Name of the collection to be deleted. Choices: "users", "datasets", "metadata", "queries_archives" (required).

- ``get_collection``: Print a collection.

  - ``-c, --collection``: Name of the collection to be shown. Choices: "users", "datasets", "metadata", "queries_archives" (required).

Examples
--------
.. code-block:: console

   # Add a user
   python mongodb_admin_cli.py add_user -u username

   # Add a user with budget
   python mongodb_admin_cli.py add_user_with_budget -u username -d dataset_name -e 0.5 -del 0.1

   # Delete a user
   python mongodb_admin_cli.py del_user -u username

   # Add a dataset to a user
   python mongodb_admin_cli.py add_dataset_to_user -u username -d dataset_name -e 0.5 -del 0.1

   # Delete a dataset from a user
   python mongodb_admin_cli.py del_dataset_to_user -u username -d dataset_name

   # Set budget field for a user and dataset
   python mongodb_admin_cli.py set_budget_field -u username -d dataset_name -f initial_epsilon -v 0.5

   # Set may query field for a user
   python mongodb_admin_cli.py set_may_query -u username -v True

   # Show user metadata
   python mongodb_admin_cli.py get_user -u username

   # Create users collection from a YAML file
   python mongodb_admin_cli.py add_users_via_yaml -yf users.yaml -c

   # Show all previous queries from user "username"
   python mongodb_admin_cli.py get_archives -u username

   # Get the list of all users
   python mongodb_admin_cli.py get_users

   # Get the list of all datasets from user "username"
   python mongodb_admin_cli.py get_user_datasets -u username

   # Add a dataset
   python mongodb_admin_cli.py add_dataset -d dataset_name -db database_type -d_path dataset_path -m_db metadata_database_type

   # Create datasets from a YAML file
   python mongodb_admin_cli.py add_datasets_via_yaml -yf datasets.yaml -c -od -om

   # Delete a dataset
   python mongodb_admin_cli.py del_dataset -d dataset_name

   # Show dataset "dataset_name"
   python mongodb_admin_cli.py get_dataset -d dataset_name

   # Show metadata for dataset "dataset_name"
   python mongodb_admin_cli.py get_metadata -d dataset_name

   # Drop a collection
   python mongodb_admin_cli.py drop_collection -c users

   # Show a collection
   python mongodb_admin_cli.py get_collection -c datasets

.. toctree::
   :maxdepth: 2

   notebooks/local_admin_notebook