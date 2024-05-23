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

3. Create a Docker Volume for MongoDB

   You need to create a Docker volume for MongoDB data persistence. 
   Run the following command:

   .. code-block:: bash

      docker volume create mongodata

4. Start the Server

   With Docker and Docker Compose set up, you can now start the server. 
   In the same directory, run:

   .. code-block:: bash

      docker compose up

5. Access the Server

   Once the server is up and running, it should be accessible on `localhost`. Open your web browser and go to:

   .. code-block:: text

      http://localhost
