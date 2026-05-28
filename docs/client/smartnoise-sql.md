# Smartnoise SQL

## Overview

SmartNoise SQL is an open-source library for executing differentially private SQL queries over tabular data. It allows users to write standard SQL queries and automatically adds calibrated noise to the results, ensuring privacy guarantees without requiring users to manually construct privacy mechanisms.

SmartNoise SQL is particularly well-suited for users already familiar with SQL, as it requires minimal changes to existing query patterns while providing strong differential privacy guarantees.

## Usage in Lomas

Users can submit SQL queries directly via the Lomas client package using the [smartnoisesql](../api/client.md/#lomas_client.libraries.smartnoise_sql) module. The query is sent to the server, which validates and executes it against the private dataset while tracking the consumed DP budget.

## Example

A worked example demonstrating how to use SmartNoise SQL through the Lomas client is available in [this notebook](../notebooks/Demo_Client_Notebook_Smartnoise-SQL.ipynb).

## References

* [Smartnoise SQL GitHub](https://github.com/opendp/smartnoise-sdk/tree/main/sql)

* [Smartnoise SQL documentation](https://docs.smartnoise.org/sql/index.html)
