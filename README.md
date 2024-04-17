# Lomas Platform

The lomas platform follows a classic server/client model.
On the client side, the researcher prepares queries for statistical analyses which are sent to the service's REST API via HTTP. The researcher never has direct access to the sensitive data.
On the server side, the service is implemented in a micro-service architecture and is thus split into two parts: the administration database and the client-facing HTTP server (which we call server for brevity) that implements the service logic.
The server is responsible for processing the client requests and updating its own state as well as administrative data (users data, budgets, query archives, etc.) in the administration database.# Lomas Platform

The lomas platform follows a classic server/client model.
The service is not responsible for storing and managing private datasets, these are usually already stored on the provider's infrastructure.
See our white paper (TODO link) for detailed explanation of the platform.


## Client package `lomas_client`

The `lomas_client` library is a client to interact with the Lomas server. It is available on Pypi. Reasearcher and Data Scientists 'using' the service to query the sensitive data will only interact with the client and never with the server.

Utilizing this client library is strongly advised for querying and interacting with the server, as it takes care of all the necessary tasks such as serialization, deserialization, REST API calls, and ensures the correct installation of other required libraries. In short, it enables a seamless interaction with the server.

For additional informations about the client, please see the [README.md](https://github.com/dscc-admin-ch/lomas/blob/master/client/README.md) of the client and for addictional examples please see the [Demo_Client_Notebook.ipynb](https://github.com/dscc-admin-ch/lomas/blob/master/client/notebooks/Demo_Client_Notebook.ipynb).


## Server

The server side, implemented in a micro-service architecture, is composed of two main services:
- A client-facing HTTP server, that uses FastAPI for processing user requests and executing diverse queries. Its primary function is to efficiently handle incoming requests from the client (researcher) and to execute the different queries (SmartnoiseSQL, OpenDP, etc.).
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


## History
The starting point of our platform was the code shared to us by [Oblivious](https://www.oblivious.com/). They originally developed a client/server platform for the [UN PET Lab Hackathon 2022](https://petlab.officialstatistics.org/).