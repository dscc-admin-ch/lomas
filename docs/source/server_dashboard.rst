Dashboard
===================================

To simplify interaction with the server, users can access a dashboard. The availability and setup of this 
dashboard vary depending on the deployment method used.

Local Access via Docker
-------------------------------

When using Docker Compose, the dashboard is locally accessible. Simply run the Docker Compose setup, and the 
dashboard will be available at localhost:8501.

Access via Kubernetes
---------------------

If you are deploying with Kubernetes, ensure that the ``create`` value is set to ``true`` in your configuration. 
If ``create`` is not set to ``true``, the server will only be accessible though the API, and the dashboard will not be available.

Access via Onyxia Platform
--------------------------

Users with access to the Onyxia platform can directly execute the dashboard here. In this platform, 
the ``create`` variable is activated by default in the configuration.
