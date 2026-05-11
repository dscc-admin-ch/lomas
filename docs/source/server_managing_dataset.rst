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
If the dataset is stored externally on a s3 instance (garage, aws, etc.)

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

Note that if your dataset is stored on a S3 bucket, other parameters should be used instead of `dataset_path`.

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

The metadata must follow the `csvw-safe` format.
See: https://github.com/dscc-admin-ch/csvw-safe.
