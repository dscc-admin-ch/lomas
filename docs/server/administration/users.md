# Managing Users via the Admin Dashboard

!!! tip "__If using Dex__"

    By default, the lifetime of tokens delivered by Dex is set very short to speed up our test runs. Make sure to change the setting (in `devenv/dex.nix`) to larger value when testing the dashboard.

## Adding a user

Adding a user works either through the straightforward "Add user" section or via the "Bulk user import" function. The bulk import method requires properly formatted yaml file listing users and the datasets accessible to them. Below is an example of such a file. You can also find the demo user collection in `server/data/collections/user_collection.yaml` while the pydantic model for users is specified in `core/lomas_core/models/collections.py`.

```yaml
- id:
    name: Alice
    email: "alice@example.com"
    client_secret: alice        # Only if using Dex, not for production.
  may_query: True
  datasets_list:                # Can be empty
  - dataset_name: "IRIS"
    initial_epsilon: 10.0
    initial_delta: 0.0001
    total_spent_epsilon: 0.0
    total_spent_delta: 0.0
  - dataset_name: "PENGUIN"
    initial_epsilon: 5.0
    initial_delta: 0.0005
    total_spent_epsilon: 0.0
    total_spent_delta: 0.0
```

## Adding datasets to users and setting DP budget

Once a user has been added, it is listed on top of the "Users" section.
Select the tickbox on the leftmost column of the table to edit a user.
The ε and δ fields in the dataset list are editable.
You can also add a new dataset to the user from the available dataset list in the box below.
For how to add new datasets to Lomas, checkout the [datasets page](datasets.md).
Finally, the previous queries button let's you display all previous queries run by that user.


## Deletion

Deletions are grouped in the last section of this page.
You can select an existing user and a dataset from its authorized list either remove the dataset from the user or delete the user entirely.
Make sure you know what you are doing before deleting anything from the admin database!

There are also bulk delete buttons to remove entire collections from the admin database.
Use these with caution!

