<h1 align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dscc-admin-ch/lomas/blob/wip_322_darkmode-logo/images/lomas_logo_darkmode_txt.png"  width="300">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/dscc-admin-ch/lomas/blob/wip_322_darkmode-logo/images/lomas_logo_txt.png"  width="300">
  <img alt="I don't know why but this is needed." src="https://user-images.githubusercontent.com/25423296/163456779-a8556205-d0a5-45e2-ac17-42d089e3c3f8.png">
</picture>
</h1><br>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/pypi/pyversions/lomas_client.svg)](https://pypi.org/project/lomas_client/)
[![Documentation](https://img.shields.io/badge/docs-Read%20the%20Docs-blue)](https://dscc-admin-ch.github.io/lomas-docs/index.html)
[![Tests](https://github.com/dscc-admin-ch/lomas/actions/workflows/test_and_coverage_server.yml/badge.svg)](https://github.com/dscc-admin-ch/lomas/actions/workflows/test_and_coverage_server.yml)
[![Coverage badge](https://raw.githubusercontent.com/dscc-admin-ch/lomas/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://raw.githubusercontent.com/dscc-admin-ch/lomas/python-coverage-comment-action-data/htmlcov/index.html)
[![CodeQL](https://github.com/dscc-admin-ch/lomas/actions/workflows/check_security_codeQL.yml/badge.svg)](https://github.com/dscc-admin-ch/lomas/actions/workflows/check_security_codeQL.yml)
[![PyPi version](https://img.shields.io/pypi/v/lomas_client.svg)](https://pypi.org/project/lomas_client/)




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
* **Technical Documentation**: https://dscc-admin-ch.github.io/lomas-docs/index.html
* **Poster**: https://github.com/dscc-admin-ch/lomas/blob/master/images/poster.pdf


## Client package `lomas_client`

The `lomas_client` library is a client to interact with the Lomas server. It is available on Pypi. Reasearcher and Data Scientists 'using' the service to query the sensitive data will only interact with the client and never with the server.

Utilizing this client library is strongly advised for querying and interacting with the server, as it takes care of all the necessary tasks such as serialization, deserialization, REST API calls, and ensures the correct installation of other required libraries. In short, it enables a seamless interaction with the server.

For additional informations about the client, please see the [README.md](https://github.com/dscc-admin-ch/lomas/blob/master/client/README.md) of the client and for addictional examples please see the [Demo_Client_Notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/client/notebooks/Demo_Client_Notebook.ipynb).


## Server

The server side, implemented in a micro-service architecture, is composed of two main services:
- A client-facing HTTP server, that uses FastAPI for processing user requests and executing diverse queries. Its primary function is to efficiently handle incoming requests from the client (user) and to execute the different queries (SmartnoiseSQL, OpenDP, etc.).
- A MongoDB administration database to manage the server state. This database serves as a repository for user and metadata about the dataset. User-related data include access permissions to specific datasets, allocated budgets for each user, remaining budgets and queries executed so far by the user (that we also refer to as "archives"). Dataset-related data includes details such as dataset names, information and credentials for accessing the sensitive dataset (e.g., S3, local, HTTP), and references to associated metadata.

The server connects to external databases, typically deployed by a data owner, to download the sensitive datasets for query execution. Currently, the server can manage adapters to S3, http file download and local files.

For extensive informations about how to administrate the MongoDB database, please refer to:
- [local_admin_notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/server/notebooks/local_admin_notebook.ipynb) for local administration of a database
- [kubernetes_admin_notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/server/notebooks/kubernetes_admin_notebook.ipynb) for administration of a database on kubernetes

## Deployment
We aim to facilitate the platform configuration, deployment and testing on commonly available IT infrastructure for NSOs and other potential users.
In this regard, we provide two Helm charts for deploying the server components (server and MongoDB database) and a client development environment in a Kubernetes cluster.

For extensive informations about how to deploy, please refer to:
- [local_deployment_notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/server/notebooks/local_deployment_notebook.ipynb) for local deployments
- [kubernetes_deployment_notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/server/notebooks/kubernetes_deployment_notebook.ipynb) for deployments on kubernetes


Finally, the service provider is responsible for deploying the service and managing users and private datasets by adding, modifying or deleting information in the administration database.
It is important to note that the service is not responsible for storing and managing private datasets, these are usually already stored on the provider's infrastructure.

## Disclaimer
Lomas is a Proof of Concept that is still under development. 

The overall infrastructure security is not our current priority.  While attention has been given to the 'logical' aspects within the server, many security aspects are not handled. For example, user authentication is not implemented. However, Lomas can be integrated into other secure infrastructures.

We welcome any feedback or suggestions for future improvements. External input is valuable as we continue to enhance the security and functionality of Lomas. Please open a bug report or issue here: https://github.com/dscc-admin-ch/lomas/issues.open.

## History
The starting point of our platform was the code shared to us by [Oblivious](https://www.oblivious.com/). They originally developed a client/server platform for the [UN PET Lab Hackathon 2022](https://petlab.officialstatistics.org/).
