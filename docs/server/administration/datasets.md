# Managing Datasets via the Admin Dashboard

## Supported storage

Lomas currently supports three options for storing datasets:

1. Local: The dataset is stored as a CSV file on a filesystem mounted on the server machine.
2. Remote dataset (HTTP): For testing purposes only, you can provide an HTTP download link as dataset path. For example, the test and demo PENGUIN dataset is loaded in this fashion.
3. Remote dataset (S3): The dataset is stored on S3 compatible storage (Garage, AWS, etc.).

## Preparing metadata

Before adding a dataset to Lomas, you should have its metadata readily available. This is required by the platform in order
to create the dummy dataset and to apply the different DP mechanisms correctly during the processing
of the queries sent by the user.

The metadata must follow the `csvw-eo` format. See https://github.com/dscc-admin-ch/csvw-eo for more information.

## Private DB credentials

Datasets stored in S3 storage require private credentials to be downloaded by the Lomas server. These credentials are not stored directly in the admin db but are injected in the server config via environment variables (see `LOMAS_SERVICE_private_db_credentials__**` environment variables.) This allows to securely store sensitive values in Kubernetes secrets or a Vault and dynamically inject them at server startup.

## Adding a dataset

The "Add dataset" section only allows adding local datasets. Similarly to bulk user import, you can import multiple dataset at once via the "Bulk datasets import" feature. This method requires properly formatted yaml file listing datasets and how to access their metadata. Below is an example of such a file. You can also find the demo dataset collection in `server/data/collections/dataset_collection.yaml` while the pydantic model for datasets is specified in `core/lomas_core/models/collections.py`.

```yaml
- dataset_name: "PENGUIN"
  dataset_access:
    database_type: "PATH_DB"
    path: "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv"
  metadata_access:
    database_type: "PATH_DB"
    path: "collections/metadata/penguin_metadata.json"
```

<!-- TODO update this once properly manage S3 credentials-->

## Deletion

Deletions are grouped in the last section of this page. You can select an existing dataset and delete it. Make sure you know what you are doing before deleting anything from the admin database!

There are also bulk delete buttons to remove entire collections from the admin database. Use these with caution!


