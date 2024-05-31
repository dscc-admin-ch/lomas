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
