# OpenDP

## Overview
[OpenDP](https://docs.opendp.org/en/v0.14.2/getting-started/index.html) is an open-source library for building differentially private computations. It provides a flexible framework for constructing privacy-preserving data analyses.

OpenDP provides differentially private implementations of common summary statistics through integrations with popular data science packages such as [Polars](https://pola.rs/), allowing users to perform familiar data analysis workflows with built-in privacy guarantees.

## Usage in Lomas

Users can submit OpenDP measurements directly via the Lomas client package using the [opendp](../api/client.md/#lomas_client.libraries.opendp) module. The query is sent to the server, which validates and executes it against the private dataset while tracking the consumed DP budget.

## Lomas specificities

The `lomas-client` package provides some useful function allowing users to directly create a DP Context that they can use to build and test their DP pipeline.

**Recommended flow**

* Get a dummy dataset: `client.get_dummy_dataset()`. This can be used to get used to the data.

* Create a `opendp.Context` that will be automatically generated based on the metadata: `client.get_context()`

* Use this context to build the opendp pipeline: `context.query().(<your_query>)`

* Test your pipeline:
    * locally: `<your_pipeline>.release().collect()`. This should help you catch potential errors before sending the request to the server.
    * on remote AND on the dummy dataset: `client.opendp.query(<your_pipeline>, dummy=True)`

* Once satisfied with the dummy results, send the query to be performed on the actual data with `dummy=False`.

!!! example

    A worked example demonstrating how to use OpenDP through the Lomas client is available in [this notebook](../notebooks/Demo_Client_Notebook_OpenDP_Polars.ipynb).

## References

* [OpenDP GitHub](https://github.com/opendp)
* [OpenDP documentation](https://docs.opendp.org/en/v0.14.2/getting-started/index.html)
