Kubernetes
==================

In this chapter, we will guide you through deploying the service on Kubernetes.
We provide a Helm chart to simplify this process.

Prerequisites
-------------

Before you begin, make sure you have the following:

1. **Kubernetes Cluster**: A running Kubernetes cluster.
    If you don't have one, you can set up a local cluster using Minikube
    or Kind, or use a cloud provider like GKE, EKS, or AKS.
2. **Helm**: Helm installed on your local machine.
    Follow the `official Helm installation guide <https://helm.sh/docs/intro/install/>`_
    if you haven't installed Helm yet.
3. **kubectl**: Kubernetes command-line tool ``kubectl``
    installed and configured to communicate with your cluster.
    You can install ``kubectl`` by following the
    `official Kubernetes installation guide
    <https://kubernetes.io/docs/tasks/tools/install-kubectl/>`_.

Deploying the Service on Kubernetes
-----------------------------------

To deploy the service on Kubernetes, follow the instructions below.

Accessing the Helm Chart
------------------------

The Helm chart for deploying the service on Kubernetes is available here:

.. code-block:: sh

    helm repo add lomas https://dscc-admin-ch.github.io/helm-charts

Modifying ``values.yaml``
-------------------------

Before installing the Helm chart, you need to adapt the ``values.yaml`` file to
fit your specific requirements, especially the ``ingress`` configuration.

Modifying the ``ingress`` Section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To change the ``ingress`` configuration, follow these steps:

1. **Get the default values**

.. code-block:: sh

    helm show values lomas/lomas-server > values.yaml

2. **Edit values.yaml file**

3. **Save the Changes**

Installing the Helm Chart
-------------------------

Once you have modified the ``values.yaml`` file, you can proceed
to install the Helm chart with your custom configurations:

1. **Install the Helm Chart**

   Navigate to the directory containing the modified ``values.yaml``
   file and run the following command:

   .. code-block:: sh

      helm install lomas-sever lomas/lomas-server -f values.yaml

By following these steps, you will have successfully configured and deployed the service
on Kubernetes using the provided Helm chart.


Kubernetes Secret Management
----------------------------

When deploying through the Helm chart, various secret values (e.g. credentials) are injected into Lomas containers at runtime.
In Kubernetes, secret values are stored separately and managed through a dedicated resource: Secrets.
Secret values are either provided to the Lomas chart directly via the values.yaml file (for testing purposes) or preferably via existing Kubernetes secrets.
The secret format is sometimes enforced by the underlying charts Lomas depends on. Here is a list of all secret resources used/created by the Lomas chart.

* **RabbitMQ**
  * Lomas relies on Bitnami's RabbitMQ chart. One secret is used for RabbitMQ's password.
  * Existing secret: The secret name can be specified with ``rabbitmq.auth.existingPasswordSecret`` while the key with ``rabbitmq.auth.existingSecretPasswordKey``.
  * Values file: ``rabbitmq.auth.password`` is used for setting the password.
* **Keycloak**
  * Lomas relies on Bitnami's Keycloak chart. One secret is used for the admin password.
  * Existing secret: The secret name can be specified with ``keycloak.auth.existingPasswordSecret`` while the key with ``keycloak.auth.existingSecretPasswordKey``.
  * Values file: ``keycloak.auth.adminPassword`` is used for setting the admin password.
* **Admin / ID Provider**
  * The Lomas admin client secret as well as the client secret for the Lomas service (server and worker) both require a secret.
  * Existing secret: In ``admin`` set ``client_secret_existing_secret`` and ``client_secret_secret_key`` for the admin client secret, and ``lomas_service_existing_secret`` and ``lomas_service_secret_key`` for the service client secret.
  * Values file: Use ``admin.client_secret`` and ``lomas_servcie_client_secret``.
* **Private DB Credentials**
  * Credentials for external private databases are read by the Lomas server and worker through their configs and thus also injected as environment variables via Kubernetes secrets.
  * For each set of credentials to a private database, one can either specify an existing secret or set the credentials as an element of the list at ``server.runtime_args.private_db_credentials``.
  * Existing secret: Add the name of the existing secret as an element of the list by adding ``existing_secret: <name of your secret>`` to the ``private_db_credentials`` list. The secret key should be ``private-db-credentials`` and contain a valid json representation of the private database credentials.
  * Values file: Directly add the dictionary representing the credentials as an element of the ``private_db_credentials`` list.
