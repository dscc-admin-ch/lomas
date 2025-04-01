Local
==================

This chapter provides instructions on how to deploy the server locally. 
Follow these steps to get your server up and running on your local machine.

Prerequisites
-------------

- Ensure you have Docker and Docker Compose installed on your system.

Steps to Deploy Locally
-----------------------

1. Clone the Repository

   First, you need to clone the repository. Open your terminal and run:

   .. code-block:: bash

      git clone https://github.com/dscc-admin-ch/lomas.git

2. Navigate to the Server Directory

   Move into the server directory where the Dockerfile is located:

   .. code-block:: bash

      cd server

3. Start the Server

   With Docker and Docker Compose set up, you can now start the server. 
   In the same directory, run:

   .. code-block:: bash

      docker compose --env-file ./configs/.env.docker-compose up

   If using devenv, this command is also provided as a utility script with `docker-compose-up`.

   Depending on the number of Docker images that must be pulled or built, the deployment process can take some time.
   The server is only started last, so please be patient!

   Note for developpers: The docker compose file is parametrized with an .env file via variable interpolation. We generate all configuration files using devenv before checking them into Git. This is specified with a note at the beginning of each of these automatically generated files.

4. Access the Server

   Once the server is up and running, it should be accessible on `localhost`. Open your web browser and go to:

   .. code-block:: text

      http://localhost:48080

5. Additional Services

   Running `docker compose up` will also start a few additional services automatically:
   * The local administration MongoDB, that relies on the docker volume `mongodata`.
   * The identity provider, Keycloak, as well as a setup container to initialize the service.
   * The messaging system, RabbitMQ.
   * A setup container that will fill up Keycloak and the administration database with demo users.
   * All the observability components (see observability).
   If the develop mode is not ON (by default in the config), the server state will be maintained across restarts.
   * A local instance of a Minio server with an `example` bucket containing the "titanic" dataset and its metadata. The dataset is automatically added to the service if the develop mode is ON (by default in the config.). One can also add data to the Minio server through its api endpoint (`http://localhost:19000`) or through the web console (`http://localhost:19001` in your browser). Make sure to use `http:minio:19000` in your config files since that is the address of the Minio server inside the local docker lomas-network network.
   * A Jupyter notebook environment that will be available at the address http://127.0.0.1:8888/ to interact as a user with the server
   * A streamlit application that will be available at the address http://localhost:8501/ to interact with the server and the administration database as an administrator.
