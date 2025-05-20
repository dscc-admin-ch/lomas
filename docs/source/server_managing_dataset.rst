Adding and referencing new dataset
========================================

This page should help the administrator to add a new dataset on the Lomas platform.


Dataset
----------
For this tuto, we'll take as example a fake dataset called fake.csv that the administrator wants to add on the platform. Three choices are possible :

1. Local dataset
For testing purpose, one can choose to add its dataset directly in the folder `server/data`.

2. Remote dataset (HTTP)
If the dataset is stored externally and can be directly downloaded online.

3. Remote dataset (S3)
If the dataset is stored externally on a s3 instance (minio, aws, etc.)

Once the type of dataset is figured out, one can modify the file `dataset_collection.yaml` in the folder `server/data/collections`.

Example with our fake dataset, the administrator needs to add this information (local example).

.. code-block:: yaml
   datasets:
   - dataset_name: "FAKE"
     database_type: "PATH_DB"
     dataset_path: "../data/datasets/fake.csv"
     metadata:
      database_type: "PATH_DB"
      metadata_path: "../data/collections/metadata/fake.yaml"
* dataset_name: Name of the given dataset
* database_type: "S3_DB" if dataset stored on a S3 bucket, otherwise "PATH_DB"
* dataset_path: Needed if database_type is "PATH_DB". For local dataset, one needs to privide the directory path to access the dataset. If HTTP, one should give the url where the dataset is stored.

Note that if your dataset is stored on a S3 bucket, other parameters should be used instead of `dataset_path`

.. code-block:: yaml
   datasets:
   - dataset_name: "FAKE"
     database_type: "S3_DB"
     bucket: your_bucket_name
     key: your_path_to_dataset #data/fake.csv
     endpoint_url: your_s3_url
     crendentials_name: your_credentials
Metadata
-----------
Each dataset should be added with its related metadata. This is required by the platform in order
to create the dummy dataset and to apply the different DP mechanisms correctly during the processing
of the queries sent by the user.

The metadata must be written into a YAML format with the following structure (example with `fake.csv`):

.. code-block:: yaml
  max_ids: 1
  rows: 300
  columns:
    profession:
      type: string
      cardinality: 2
      categories: ["teacher", "researcher"]
      max_partition_length: 0.6
      max_influenced_partitions: 1
      max_partition_contributions: 1
      # precision:
      # upper:
      # lower:
    region:
      ...
This format is based on the `SmartnoiseSQL dictionary format <https://docs.smartnoise.org/sql/metadata.html#dictionary-format>`_ with added options for Lomas.

Table options:

* `max_ids`: Specify how many rows each unique user can appear in (cf. Smartnoise documentation)
* `rows`: Required. The number of rows in the dataset. If the administrator does not know or do not want to share how many records are in the data, she can specify a very loose upper bound.

Column options:

* `private_id`: Default is `False`.
* `type`: Required. Options : ["int", "float", "string", "boolean", "datetime"]
* `precision`: Required if type is either "int" or "float". Options: 32 or 64.
* `upper`: Required if column type is numeric. Specify the upper bound of the column.
* `lower`: Required if column type is numeric. Specify the lower bound of the column.
* `cardinality`: Required if column type is categorical. Specify the number of categories in the column.
* `categories`: Required if column type is categorical. Specify the list of category (ex: ["blue","red","yellow"])
* `max_partition_length`: Optional. Default is set to 1. An upper bound on the number of records in any one partition. (in %). (Source: `OpenDP <https://docs.opendp.org/en/stable/api/python/opendp.extras.polars.html>`_ )
* `max_influenced_partitions:` Optional. The greatest number of partitions any one individual can contribute to. (Source: `OpenDP <https://docs.opendp.org/en/stable/api/python/opendp.extras.polars.html>`_ )
* `max_partition_contributions`: Optional. The greatest number of records an individual may contribute to any one partition. (Source: `OpenDP <https://docs.opendp.org/en/stable/api/python/opendp.extras.polars.html>`_ )
* `max_num_partitions`: Optional. The greatest number of distinct partitions (similar to cardinality) (Source: `OpenDP <https://docs.opendp.org/en/stable/api/python/opendp.extras.polars.html>`_ )




Code
----------
TODO