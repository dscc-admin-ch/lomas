.. Lomas documentation master file, created by
   sphinx-quickstart on Wed May 28 09:18:59 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Lomas: The Data Oases Hidden Behind the Mist.
========================================
Lomas is a platform for remote data science, enabling sensitive data to be querried remotely 
while staying protected by a layer of differential privacy.

The lomas platform follows a classic server/client model. On the client side, the 
user prepares queries for statistical analyses which are sent to the 
service's REST API via HTTP. The user never has direct access to the sensitive 
data. On the server side, the service is implemented in a micro-service architecture and is 
thus split into two parts: the administration database and the client-facing HTTP server 
(which we call server for brevity) that implements the service logic. The server 
is responsible for processing the client requests and updating its own state as 
well as administrative data (users data, budgets, query archives, etc.) in 
the administration database.

The service is not responsible for storing and managing private datasets, 
these are usually already stored on the provider's infrastructure. 

.. See our white paper (TODO link) for detailed explanation of the platform.

You can find our `GitHub repository <https://github.com/dscc-admin-ch/lomas/tree/master/>`_
following this link.

Client
========
The ``lomas_client`` library is a client to interact with the Lomas server. It is available on 
Pypi. Reasearcher and Data Scientists 'using' the service to query the sensitive data will 
only interact with the client and never with the server.

Utilizing this client library is strongly advised for querying and interacting with the 
server, as it takes care of all the necessary tasks such as serialization, deserialization, 
REST API calls, and ensures the correct installation of other required libraries. In short, 
it enables a seamless interaction with the server.

For additional informations about the client, please see the 
`README.md <https://github.com/dscc-admin-ch/lomas/blob/master/client/README.md>`_ of 
the client and for additional examples please see the 
:doc:`examples <client_examples>` section.


Server
========
The server side, implemented in a micro-service architecture, is composed of two main services:

- A client-facing HTTP server, that uses FastAPI for processing user requests and executing diverse queries. 
Its primary function is to efficiently handle incoming requests from the client (user) and to execute the different 
queries (SmartnoiseSQL, OpenDP, etc.).

- A MongoDB administration database to manage the server state. This database serves as a repository for user and metadata about the dataset. User-related data include access permissions to specific datasets, allocated budgets for each user, remaining budgets and queries executed so far by the user (that we also refer to as "archives"). Dataset-related data includes details such as dataset names, information and credentials for accessing the sensitive dataset (e.g., S3, local, HTTP), and references to associated metadata.


The server connects to external databases, typically deployed by a data owner, to download the 
sensitive datasets for query execution. Currently, the server can manage adapters to S3, 
http file download and local files.

For extensive informations about how to administrate the MongoDB database, 
please refer to :doc:`Administration <server_administration>` section.

We aim to facilitate the platform configuration, deployment and testing on commonly available 
IT infrastructure for NSOs and other potential users.

In this regard, we provide two Helm charts for deploying the server components (server and 
MongoDB database) and a client development environment in a Kubernetes cluster.

For extensive informations about how to deploy, please refer to :doc:`Deployment <server_deployment>`
documentation.

History
========
The starting point of our platform was the code shared to us by `Oblivious <https://www.oblivious.com/>`_.

They originally developed a client/server platform for the `UN PET Lab Hackathon 2022 <https://petlab.officialstatistics.org/>`_.

.. toctree::
   :maxdepth: 2
   :caption: Client
   :hidden:

   client_quickstart
   client_examples
   client_errors

.. toctree::
   :maxdepth: 2
   :caption: Server
   :hidden:

   server_deployment
   server_administration

.. toctree::
   :maxdepth: 2
   :caption: Python API
   :hidden:

   api

.. toctree::
   :maxdepth: 2
   :caption: Contributing
   :hidden:

   CONTRIBUTING.md
   CONTRIBUTING_CLIENT.md
   CONTRIBUTING_SERVER.md

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
