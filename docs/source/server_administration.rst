Administration
==============

This section explains how the data owner can manage the administrative database as well as the Lomas keycloak realm.
It covers some tasks such as adding data, making data available to certain users,
managing the budget, etc.

The administration of the Lomas service is handled through a dedicated dashboard. Access is described below.
In addition, all administration tools are implemented in ``lomas_server.administration``,
one can thus execute the same tasks by writing a python script / notebook that uses these methods.


Dashboard Access when deploying via devenv
------------------------------------------

When running with devenvThe dashboard is accessible on the localhost at the port specified at the top of the devenv.nix file.

Dashboard Access when deploying via Docker compose
--------------------------------------------------

When using Docker Compose, the dashboard is locally accessible. Simply run the Docker Compose setup, and the
dashboard will be available at ``localhost:8501``.

Dashboard Access when deploying via Kubernetes
----------------------------------------------

If you are deploying with Kubernetes, ensure that the ``dashboard.create`` value is set to ``true`` in your values.yaml.
If ``dashboard.create`` is not set to ``true``, the server will only be accessible though the API, and the dashboard will not be available.

Access via Onyxia Platform
--------------------------

Users with access to the Onyxia platform can directly execute the dashboard here. In this platform,
the ``create`` variable is activated by default in the dashboard configuration.