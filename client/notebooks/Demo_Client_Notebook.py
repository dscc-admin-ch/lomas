import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Lomas: Client demo
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook showcases how researcher could use the Lomas platform. It explains the different functionnalities provided by the `lomas-client` library to interact with the secure server.

    The secure data are never visible by researchers. They can only access to differentially private responses via queries to the server.

    Each user has access to one or multiple projects and for each dataset has a limited budget with $\epsilon$ and $\delta$ values.
    """)


@app.cell
def _(mo):
    mo.image("images/image_demo_client.png", width=800)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    🐧🐧🐧
    In this notebook the researcher is a penguin researcher named Dr. Antarctica. She aims to do a grounbdbreaking research on various penguins dimensions.

    Therefore, the powerful queen Icerbegina 👑 had the data collected. But in order to get the penguins to agree to participate she promised them that no one would be able to look at the data and that no one would be able to guess the bill width of any specific penguin (which is very sensitive information) from the data. Nobody! Not even the researchers. The queen hence stored the data on the Secure Data Disclosure Server and only gave a small budget to Dr. Antarctica.

    This is not a problem for Dr. Antarctica as she does not need to see the data to make statistics thanks to the Secure Data Disclosure Client library `lomas-client`.
    🐧🐧🐧
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 1: Install the library
    To interact with the secure server on which the data is stored, Dr.Antartica first needs to install the library `lomas-client` on her local developping environment.

    It can be installed via the pip command:
    """)


@app.cell
def _():
    # !pip install lomas-client
    return


@app.cell
def _():
    # magic command not supported in marimo; please file an issue to add support
    # %load_ext autoreload
    # '%autoreload 2' command supported automatically in marimo

    import numpy as np

    from lomas_client import Client

    return Client, np


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 2: Initialise the client

    Once the library is installed, a Client object must be created. It is responsible for sending sending requests to the server and processing responses in the local environment. It enables a seamless interaction with the server.

    The client needs a few parameters to be created. Usually, these would be set in the environment by the system administrator (queen Icebergina) and be transparent to lomas users. In this instance, the following code snippet sets a few of these parameters that are specific to this notebook.

    She will only be able to query on the real dataset if the queen Icebergina has previously made her an account in the database, given her access to the PENGUIN dataset and has given her some epsilon and delta credit.
    """)


@app.cell
def _():
    # The following would usually be set in the environment by a system administrator
    # and be tranparent to lomas users.
    # Uncomment them if you are running against a Kubernetes deployment.
    # They have already been set for you if you are running locally within a devenv or the Jupyter lab set up by Docker compose.

    import os
    # os.environ["LOMAS_CLIENT_APP_URL"] = "https://lomas.example.com:443"
    # os.environ["LOMAS_CLIENT_OIDC_DISCOVERY_URL"] = "https://dex.example.com:443/.well-known/openid-configuration"
    # os.environ["LOMAS_CLIENT_TELEMETRY__ENABLED"] = "false"
    # os.environ["LOMAS_CLIENT_TELEMETRY__COLLECTOR_ENDPOINT"] = "http://otel.example.com:445"
    # os.environ["LOMAS_CLIENT_TELEMETRY__COLLECTOR_INSECURE"] = "true"
    # os.environ["LOMAS_CLIENT_TELEMETRY__SERVICE_ID"] = "my-app-client"
    # os.environ["LOMAS_CLIENT_REALM"] = "lomas"

    # We set these ones because they are specific to this notebook.

    os.environ["LOMAS_CLIENT_USER_NAME"] = "dr.antartica@example.com"
    os.environ["LOMAS_CLIENT_USER_PASSWORD"] = "dr.antartica"
    os.environ["LOMAS_CLIENT_DATASET_NAME"] = "PENGUIN"

    # Note that all client settings can also be passed as keyword arguments to the Client constructor.
    # eg. client = Client(user_name = "Dr.Antartica") takes precedence over setting the "LOMAS_CLIENT_USER_NAME"
    # environment variable.


@app.cell
def _(Client):
    client = Client()
    return (client,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    And that's it for the preparation. She is now ready to use the various functionnalities offered by `lomas_client`.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 3: Understand the functionnalities of the library
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### a. Getting dataset metadata

    Dr. Antartica has never seen the data and as a first step to understand what is available to her, she would like to check the metadata of the dataset. Therefore, she just needs to call the `get_dataset_metadata()` function of the client. As this is public information, this does not cost any budget.

    This function returns metadata information in a format based on [SmartnoiseSQL dictionary format](https://docs.smartnoise.org/sql/metadata.html#dictionary-format), where among other, there is information about all the available columns, their type, bound values (see Smartnoise page for more details). Any metadata is required for Smartnoise-SQL is also required here and additional information such that the different categories in a string type column column can be added.
    """)


@app.cell
def _(client):
    penguin_metadata = client.get_dataset_metadata()
    penguin_metadata
    return (penguin_metadata,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Based on this Dr. Antartica knows that there are 7 columns, 3 of string type (species, island, sex) with their associated categories (i.e. the species column has 3 possibilities: 'Adelie', 'Chinstrap', 'Gentoo') and 4 of float type (bill length, bill depth, flipper length and body mass) with their associated bounds (i.e. the body mass of penguin ranges from 2000 to 7000 gramms). She also knows based on the field `max_ids: 1` that each penguin can only be once in the dataset and on the field `row_privacy: True` that each row represents a single penguin. Finally, she learns that there are 344 rows in the dataset and hence 344 penguins.
    """)


@app.cell
def _(penguin_metadata):
    NB_PENGUINS = penguin_metadata["publicLength"]
    NB_PENGUINS
    return (NB_PENGUINS,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### b. Get a dummy dataset

    Now, that she has seen and understood the metadata, she wants to get an even better understanding of the dataset (but is still not able to see it). A solution to have an idea of what the dataset looks like it to create a dummy dataset.

    Based on the public metadata of the dataset, a random dataframe can be created created. By default, there will be 100 rows and the seed is set to 42 to ensure reproducibility, but these 2 variables can be changed to obtain different dummy datasets.
    Getting a dummy dataset does not affect the budget as there is no differential privacy here. It is not a synthetic dataset and all that could be learn here is already present in the public metadata (it is created randomly on the fly based on the metadata).

    Dr. Antartica first create a dummy dataset with 100 rows and chooses a seed of 0.
    """)


@app.cell
def _():
    NB_ROWS = 100
    SEED = 0
    return NB_ROWS, SEED


@app.cell
def _(NB_ROWS, SEED, client):
    df_dummy = client.get_dummy_dataset(nb_rows=NB_ROWS, seed=SEED)

    print(df_dummy.shape)
    df_dummy.head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### c. Check privacy loss budget ε, δ (initial, current, remaining)
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    It is the first time that Dr. Antartica connects to the server and she wants to know how much buget has beeen assigned to her.
    Therefore, she calls the fonction `get_initial_budget`.
    """)


@app.cell
def _(client):
    client.get_initial_budget()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She sees that she has 10.0 epsilon and 0.005 epsilon at her disposal.

    Then she checks her total spent budget `get_total_spent_budget`. As she only did queries on metadata on dummy dataframes, this should still be 0.
    """)


@app.cell
def _(client):
    client.get_total_spent_budget()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    It will also be useful to know what the remaining budget is. Therefore, she calls the function `get_remaining_budget`. It just substarcts the total spent budget from the initial budget.
    """)


@app.cell
def _(client):
    client.get_remaining_budget()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    As expected, for now the remaining budget is equal to the inital budget.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 4: Use DP libraries to analyse the dataset
    Available DP libraires are:
    - Smartnoise-SQL for SQL-like queries
    - Smartnoise-Synth for generating synthetic datasets
    - OpenDP for summary statistics
    - DiffPrivLib for training Machine Learning models
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    For each library, there are three possibilities:
    - estimate the cost of a query (will NOT spend privacy loss budget)
    - query on a 'dummy' dataset (explained below) (will NOT spend privacy loss budget)
    - query on the private dataset (WILL SPEND PRIVACY LOSS BUDGET)
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### a. Compute average bill length with Smartnoise-SQL
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Dr. Antartica wants to know the average bill length of penguins. Therefore, she will use `smartnoise-sql` library and write the associated SQL command.
    """)


@app.cell
def _():
    # Average bill length in mm
    QUERY = "SELECT AVG(bill_length_mm) AS avg_bill_length_mm FROM df"
    return (QUERY,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Estimate cost of a query with smartnoise-sql
    She will then estimate the cost of this query. In the various DP librairies the budget that will by used by a query in the server might be slightly different than what is asked by the user in inptu. The `estimate cost` function of each library returns the cost that will effectively be sent and deduced if the query is applied on the sensitive dataset.

    The user can then decide to use the budget or modify it. Again, of course, this will not impact the user's budget.

    Dr. Antartica checks the budget that computing the average bill length will really cost her if she asks the query with an `epsilon` and a `delta`.
    """)


@app.cell
def _():
    EPSILON = 0.5
    DELTA = 1e-4
    return DELTA, EPSILON


@app.cell
def _(DELTA, EPSILON, QUERY, client):
    cost = client.smartnoise_sql.cost(query=QUERY, epsilon=EPSILON, delta=DELTA)
    cost
    return (cost,)


@app.cell
def _(cost):
    print(f"This query would actually cost her {cost.epsilon} epsilon and {cost.delta} delta.")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She decides that it is good enough.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Query average bill length on dummy dataset with smartnoise-sql
    She now wants to start querying the real dataset for her research.

    However, her budget is limited and it would be a waste to spend it by mistake on a coding error. Therefore the client/server pipeline has functionnal testing capabilities for the users. It is possible to test a query on a `dummy` dataset to ensure that everything is working properly. Dr. Antartica will not be able to use the results of a dummy query for her analysis (as the data is random) but if the query on the dummy dataset works, she can be confident that her query will also work on the real dataset.
    This functionnal testing on the dummy does not have any impact on the budget as it is on random data only.

    To test on the dummy data instead of the real data, the function call is exactly the same with the only exception of the flag `dummy=True`. In the following cell, she will test with `smartnoise_query` but it is the same flag for `opendp.query`. She can optionnaly give two additional parameters to set the seed and the number of rows of the dummy dataset.

    Another more advanced possibility for functionnal tests with the dummy is to compare results of queries on a local dummy and the remote dummy with a very high budget:
    - create a local dummy on the notebook with a specific seed and number of rows
    - compute locally the wanted query on this local dummy with python functions like numpy
    - query the server on the same remote dummy with (`dummy=True`, same seed and same number of row) and a very big buget to limit noise as much as possible (don't worry this won't cost any real budget)
    - compare and verify that the local and remote dummy have similar results.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Dr. Antartica will follow the best practice and now try the query to get the average bill length (in mm) on the dummy dataset. She does not forget to
    - set the `dummy` flag to True
    - set very high budget values to be able to compare results with a similar local dummy (with the same seed and number of rows) if she wants to verify that the function do what is expected. Here she will just check that the number of rows is close to what she sets as parameter.
    """)


@app.cell
def _(NB_ROWS, QUERY, SEED, client):
    # On the remote server dummy dataframe
    dummy_res = client.smartnoise_sql.query(
        query=QUERY, epsilon=100.0, delta=0.99, dummy=True, nb_rows=NB_ROWS, seed=SEED
    )
    return (dummy_res,)


@app.cell
def _(dummy_res, np):
    print(
        f"Average bill length in remote dummy: {np.round(dummy_res.result.df['avg_bill_length_mm'][0], 2)}mm."
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    No functionnal errors happened and the average bill length is within reasonable bounds. She is now even more confident in using her query on the server.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Query average bill length on private dataset with smartnoise-sql
    Now that all the safeguard functions were tested, Dr. Antartica is ready to query on the real dataset and get a differentially private response of the number of penguins and average bill length. By default, the flag `dummy` is False so setting it is optional. She uses the values of `epsilon` and `delta` that she selected just before.

    Careful: This command DOES spend the budget of the user and the remaining budget is updated for every query.
    """)


@app.cell
def _(client):
    client.get_remaining_budget()


@app.cell
def _(DELTA, EPSILON, QUERY, client):
    response = client.smartnoise_sql.query(
        query=QUERY,
        epsilon=EPSILON,
        delta=DELTA,
        dummy=False,  # APPLIED ON SENSITIVE DATA, WILL SPEND BUDGET
    )
    return (response,)


@app.cell
def _(np, response):
    avg_bill_length = np.round(response.result.df["avg_bill_length_mm"].iloc[0], 2)
    print(f"Average bill length of penguins in real data: {avg_bill_length}mm.")
    return (avg_bill_length,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    After each query on the real dataset, the budget informations are also returned to the researcher. It is possible possible to check the remaining budget again afterwards:
    """)


@app.cell
def _(client):
    client.get_remaining_budget()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    As can be seen in `get_total_spent_budget()`, it is the budget estimated with `estimate_smartnoise_cost()` that was spent.
    """)


@app.cell
def _(client):
    client.get_total_spent_budget()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Dr. Antartica has now a differentially private estimation of the number of penguins in the dataset and is confident to use the library for the rest of her analyses.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### b. Compute confidence interval with opendp
    """)


@app.cell
def _():
    import polars as pl

    return (pl,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She now wants the confidence interval of bill length in mm. She already has the number of penguins and the average from the metadata and previous smartnoise-sql queries respectively. She now needs the variance value.

    #### Prepare opendp pipeline and verify on dummy
    She checks the metadata of the columns again to use the relevant values in the pipeline.
    """)


@app.cell
def _(penguin_metadata):
    penguin_metadata["tableSchema"]["columns"]


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She can define the columns names and the bounds of the relevant column.
    """)


@app.cell
def _(penguin_metadata):
    column_names = [col["name"] for col in penguin_metadata["tableSchema"]["columns"]]
    column_names


@app.cell
def _(client):
    bill_length_meta = client.get_column_metadata("bill_length_mm")
    bill_length_meta
    return (bill_length_meta,)


@app.cell
def _(bill_length_meta):
    bill_length_min, bill_length_max = bill_length_meta["minimum"], bill_length_meta["maximum"]
    bill_length_min, bill_length_max
    return bill_length_max, bill_length_min


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Because there is no direct method for computing the variance, she decomposes it as follows:

    $Var(X) = \frac{1}{N}\sum{x_i^2} - (\frac{1}{N}\sum{x_i})^2$

    Since she already knows $N$, she needs two more dp measurements on the bill length column: one for the sum of squares and one for the sum.
    """)


@app.cell
def _(bill_length_max, bill_length_min, client, pl):
    context_sum_squared = client.get_context(epsilon=10.0)
    plan_sum_squared = (
        context_sum_squared.query()
        .with_columns(squared=pl.col.bill_length_mm.mul(pl.col.bill_length_mm))
        .select(pl.col.squared.dp.sum(bounds=(bill_length_min**2, bill_length_max**2)))
    )
    sum_squared_dummy = client.opendp.query(plan_sum_squared, epsilon=10.0, dummy=True).result.value.item()

    context_sum = client.get_context(epsilon=5.0)
    plan_sum = context_sum.query().select(
        pl.col("bill_length_mm").dp.sum(bounds=(bill_length_min, bill_length_max))
    )
    sum_dummy = client.opendp.query(plan_sum, epsilon=5.0, dummy=True).result.value.item()
    return plan_sum, plan_sum_squared, sum_dummy, sum_squared_dummy


@app.cell
def _(NB_PENGUINS, sum_dummy, sum_squared_dummy):
    var_dummy = 1 / NB_PENGUINS * sum_squared_dummy - 1 / NB_PENGUINS**2 * sum_dummy
    print(f"Bill length variance for dummy dataset: {var_dummy}")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Execute pipeline on real dataset with OpenDP

    She checks her remaining budget before running on the real dataset:
    """)


@app.cell
def _(client):
    client.get_remaining_budget()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She can now run the same queries on the real dataset:
    """)


@app.cell
def _(NB_PENGUINS, client, plan_sum, plan_sum_squared):
    sum_squared_dp = client.opendp.query(plan_sum_squared, epsilon=10.0).result.value.item()
    sum_dp = client.opendp.query(plan_sum, epsilon=5.0).result.value.item()

    var_bill_length = 1 / NB_PENGUINS * sum_squared_dp - 1 / NB_PENGUINS**2 * sum_dp
    return (var_bill_length,)


@app.cell
def _(var_bill_length):
    print(f"Variance of bill length: {var_bill_length} (from opendp query).")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Postprocessing: no additional privacy risk with DP
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She can now do all the postprocessing that she wants with the returned data without adding any privacy risk.
    """)


@app.cell
def _(NB_PENGUINS, np, var_bill_length):
    # Get standard error
    standard_error = np.sqrt(var_bill_length / NB_PENGUINS)
    print(f"Standard error of bill length: {np.round(standard_error, 2)}.")
    return (standard_error,)


@app.cell
def _(avg_bill_length, np, standard_error):
    # Compute the 95% confidence interval
    ZSCORE = 1.96
    lower_bound = np.round(avg_bill_length - ZSCORE * standard_error, 2)
    upper_bound = np.round(avg_bill_length + ZSCORE * standard_error, 2)
    print(
        f"The 95% confidence interval of the bill length of all penguins is [{lower_bound}, {upper_bound}]."
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### c. Train a DP Machine Learning model with DiffPrivLib
    """)


@app.cell
def _():
    import pandas as pd
    from diffprivlib import models
    from sklearn.pipeline import Pipeline

    return Pipeline, models, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She now wants a model to predict the species of a penguin based on bill depth. Therefore, she uses a Random Forest classifier from DiffPrivLib library.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Prepare Random Forest Classifier pipeline on dummy with DiffPrivLib
    """)


@app.cell
def _():
    feature_columns = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    target_columns = ["species"]
    return feature_columns, target_columns


@app.cell
def _(client, feature_columns):
    bounds = client.get_diffprivlib_bounds(feature_columns)
    bounds
    return (bounds,)


@app.cell
def _(client):
    species_metadata = client.get_column_metadata("species")
    species_metadata
    return (species_metadata,)


@app.cell
def _(Pipeline, bounds, models, species_metadata):
    dpl_pipeline = Pipeline(
        [
            (
                "rf",
                models.RandomForestClassifier(
                    n_estimators=10, epsilon=2.0, bounds=bounds, classes=species_metadata["keyValues"]
                ),
            ),
        ]
    )
    return (dpl_pipeline,)


@app.cell
def _(client, dpl_pipeline, feature_columns, target_columns):
    dummy_response = client.diffprivlib.query(
        pipeline=dpl_pipeline,
        feature_columns=feature_columns,
        target_columns=target_columns,
        test_size=0.2,
        test_train_split_seed=1,
        dummy=True,
    )
    model = dummy_response.result.model
    model


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Estimate budget of Linear Regression with DiffPrivLib
    """)


@app.cell
def _(client, dpl_pipeline, feature_columns, target_columns):
    cost_res = client.diffprivlib.cost(
        dpl_pipeline,
        feature_columns=feature_columns,
        target_columns=target_columns,
        test_size=0.2,
        test_train_split_seed=1,
    )
    cost_res


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Train random forest classifier on sensitive data with DiffPrivLib
    """)


@app.cell
def _(client, dpl_pipeline, feature_columns, target_columns):
    response_1 = client.diffprivlib.query(
        pipeline=dpl_pipeline,
        feature_columns=feature_columns,
        target_columns=target_columns,
        test_size=0.1,
        test_train_split_seed=1,
        dummy=False,
    )
    return (response_1,)


@app.cell
def _(response_1):
    # Return the mean accuracy.
    model_score = response_1.result.score
    return (model_score,)


@app.cell
def _(model_score, np):
    f"The model has a mean accuracy of {np.round(model_score, 2)}. It is a harsh metric because we are in a multi-label classification case."


@app.cell
def _(response_1):
    model_1 = response_1.result.model
    model_1
    return (model_1,)


@app.cell
def _(model_1, pd):
    x_to_predict = pd.DataFrame(
        {
            "bill_length_mm": [30.0],
            "bill_depth_mm": [20.0],
            "flipper_length_mm": [170.0],
            "body_mass_g": [5000.0],
        }
    )
    predictions = model_1.predict(x_to_predict)[0]
    f"For these feature values, the predicted species is is {predictions}."


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### d. Get a Synthetic Dataset with Smartnoise-Synth
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Finally she gets a synthetic dataset to do the rest of her analysis. She chooses to only train on a subset on 3 columns: "island", "bill_length_mm" and "bill_depth_mm" but if we wanted she could train on the whole dataset.
    She also decides to use the `patectgan` synthesizer and keep all other default parameters.
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Train patectgan synthesizer on dummy data with Smartnoise-Synth
    """)


@app.cell
def _():
    # TODO replace with opendp synth once supported
    # res_dummy = client.smartnoise_synth.query(
    #     synth_name="patectgan",
    #     select_cols = ["island", "bill_length_mm", "bill_depth_mm"],
    #     epsilon=1.0,
    #     dummy=True,
    # )
    # dummy_synth_df = res_dummy.result.df_samples
    return


@app.cell
def _():
    # dummy_synth_df.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Estimate cost of training patectgan synthesizer with Smartnoise-Synth
    """)


@app.cell
def _():
    # res_cost = client.smartnoise_synth.cost(
    #     synth_name="patectgan",
    #     epsilon=1.0,
    #     select_cols = ["island", "bill_length_mm", "bill_depth_mm"],
    # )
    # res_cost
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Train patectgan synthesizer on private data with Smartnoise-Synth
    """)


@app.cell
def _():
    # res = client.smartnoise_synth.query(
    #     synth_name="patectgan",
    #     select_cols = ["island", "bill_length_mm", "bill_depth_mm"],
    #     epsilon=1.0,
    #     dummy=False,
    # )
    # synth_df = res.result.df_samples
    return


@app.cell
def _():
    # synth_df.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Out of curiosity, she checks the average bill length and variance of bill length on this dataset.
    """)


@app.cell
def _():
    # synth_mean = np.round(synth_df["bill_length_mm"].mean(), 2)
    # synth_variance = np.round(synth_df["bill_length_mm"].var(), 2)
    return


@app.cell
def _():
    # print(
    #     f"The average with Smartnoise-SQL on private data was {avg_bill_length}.\n"
    #     + f"The average with Smartnoise-Synth on synthetic data is {synth_mean}."
    # )
    return


@app.cell
def _():
    # print(
    #     f"The variance with opendp on private data was {var_bill_length}.\n"
    #     + f"The variance with Smartnoise-Synth on synthetic data is {synth_variance}."
    # )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 4: See archives of queries
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    She now wants to verify all the queries that she did on the real data. It is possible because an archive of all queries is kept in a secure database. With a function call she can see her queries, budget and associated responses.
    """)


@app.cell
def _(client):
    previous_queries = client.get_previous_queries()
    len(previous_queries)
    return (previous_queries,)


@app.cell
def _(previous_queries):
    # Smartnoise-SQL
    avg_bill_length_query = previous_queries[0]
    avg_bill_length_query


@app.cell
def _(previous_queries):
    # OpenDP
    var_bill_length_query_1 = previous_queries[1]
    var_bill_length_query_1


@app.cell
def _(previous_queries):
    # DiffPrivLib
    reg_bill_length_query = previous_queries[3]
    reg_bill_length_query


@app.cell
def _():
    # Smartnoise-Synth
    # sysynth_query = previous_queries[3]
    # sysynth_query
    return


if __name__ == "__main__":
    app.run()
