# Diffprivlib

## Overview

[DiffPrivLib](https://github.com/IBM/differential-privacy-library) is an open-source differential privacy library developed by IBM. It provides some differentially private tools, including DP implementations of common machine learning algorithms and statistical analysis functions, making it familiar to users used to work with scikit-learn.

## Usage in Lomas

Users can send DiffPrivLib queries directly via the Lomas client package with `client.diffprivlib.query()` using the [diffprivlib](../api/client.md/#lomas_client.libraries.diffprivlib) module. The query is sent to the server, which validates and executes it against the private dataset while tracking the consumed DP budget.

!!! example

    A worked example demonstrating how to use DiffPrivLib through the Lomas client is available in [this notebook](../notebooks/Demo_Client_Notebook_DiffPrivLib.ipynb).

## References

* [Diffprivlib GitHub](https://github.com/IBM/differential-privacy-library)
* [Diffprivlib Documentation](https://diffprivlib.readthedocs.io/en/latest/)
