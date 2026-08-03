<h1 align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dscc-admin-ch/lomas/blob/master/images/lomas_logo_darkmode_txt.png"  width="300">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/dscc-admin-ch/lomas/blob/master/images/lomas_logo_txt.png"  width="300">
  <img alt="Lomas logo." src="https://user-images.githubusercontent.com/25423296/163456779-a8556205-d0a5-45e2-ac17-42d089e3c3f8.png">
</picture>
</h1><br>

![GitHub License](https://img.shields.io/github/license/dscc-admin-ch/lomas)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lomas_client)
[![Documentation](https://img.shields.io/badge/docs-Read%20the%20Docs-blue)](https://dscc-admin-ch.github.io/lomas/index.html)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/dscc-admin-ch/lomas/test_and_coverage_server.yml?logo=github&label=Server%20Tests)
[![Coverage badge](https://raw.githubusercontent.com/dscc-admin-ch/lomas/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://raw.githubusercontent.com/dscc-admin-ch/lomas/python-coverage-comment-action-data/htmlcov/index.html)
[![CodeQL](https://github.com/dscc-admin-ch/lomas/actions/workflows/check_security_codeQL.yml/badge.svg)](https://github.com/dscc-admin-ch/lomas/actions/workflows/check_security_codeQL.yml)
![PyPI - Version](https://img.shields.io/pypi/v/lomas_client)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# Lomas: The Data Oases Hidden Behind the Mist.

Lomas is a platform for remote data science, enabling sensitive data to be queried remotely while staying protected by a layer of differential privacy.

#### Technical Overview:

The lomas platform follows a classic server/client model.
On the client side, the user prepares queries for statistical analyses which are sent to the service's REST API via HTTP. The user never has direct access to the sensitive data.
On the server side, the service is implemented in a micro-service architecture and is thus split into two parts: the administration database and the client-facing HTTP server (which we call server for brevity) that implements the service logic.
The server is responsible for processing the client requests and updating its own state as well as administrative data (users data, budgets, query archives, etc.) in the administration database.

The service is not responsible for storing and managing private datasets, these are usually already stored on the provider's infrastructure.

#### Detailed description:

For a detailed description, please see the links below.

* **Lomas Project White Paper**: https://arxiv.org/abs/2406.17087
* **Swiss Federal Statistical Office Blog**: https://www.bfs.admin.ch/bfs/en/home/dscc/blog/2024-03-lomas.html
* **Technical Documentation**: https://dscc-admin-ch.github.io/lomas/latest
* **Poster**: https://github.com/dscc-admin-ch/lomas/blob/master/images/poster.pdf


## Client package `lomas_client`

The `lomas_client` library is a client to interact with the Lomas server. It is available on Pypi. Reasearcher and Data Scientists 'using' the service to query the sensitive data will only interact with the client and never with the server.

Utilizing this client library is strongly advised for querying and interacting with the server, as it takes care of all the necessary tasks such as serialization, deserialization, REST API calls, and ensures the correct installation of other required libraries. In short, it enables a seamless interaction with the server.

For additional informations about the client, please see the [README.md](https://github.com/dscc-admin-ch/lomas/blob/master/client/README.md) of the client and for addictional examples please see the [Demo_Client_Notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/client/notebooks/Demo_Client_Notebook.ipynb).


## Server

The server is implemented in a micro-service architecture and is thus split into multiple parts:

- The client-facing HTTP server (which we call server for brevity) handles incoming requests and manages the administration database (Python Shelf).
- The administration database: as stated above, it is directly managed by the server and persisted on local disk (Python Shelf). The database serves as a repository for users and metadata about the datasets. User-related data include access permissions to specific datasets, allocated and used DP-budgets as well as query archives (past executed queries and their result). User role is also stored in the database (ie. admin or standard user). Dataset-related data includes information such as dataset names, links to credentials for accessing the sensitive datasets and dataset metadata for DP-related operations.
- The workers run user queries.
- The admin dashboard provides a graphical interface for Lomas administrators to interact with the server. User creation, budget updates as well as dataset updates can all be executed through the dashboard.
- Telemetry: All components send metrics and logs to Opentelemetry-collector. The Grafana dashboard can be used to visualize the collected data.

Lomas is not responsible for storing and managing private datasets, these are usually already stored on the provider's infrastructure (private database in the sketch above). We currently implement adapters to S3 storage, http file download and local files.

## Deployment
We aim to facilitate the platform configuration, deployment and testing on commonly available IT infrastructure for NSOs and other potential users.
In this regard, we provide two Helm charts for deploying the server components and a client development environment in a Kubernetes cluster.

For extensive informations about how to deploy, please refer to our [online documentation](https://dscc-admin-ch.github.io/lomas/latest).


## Disclaimer
Lomas is a Proof of Concept that is still under development.

The overall infrastructure security is not our current priority.  While attention has been given to the 'logical' aspects within the server, many security aspects are not handled. For example, user authentication is not implemented. However, Lomas can be integrated into other secure infrastructures.

We welcome any feedback or suggestions for future improvements. External input is valuable as we continue to enhance the security and functionality of Lomas. Please open a bug report or issue here: https://github.com/dscc-admin-ch/lomas/issues#open.

## History
The starting point of our platform was the code shared to us by [Oblivious](https://www.oblivious.com/). They originally developed a client/server platform for the [UN PET Lab Hackathon 2022](https://petlab.officialstatistics.org/).
