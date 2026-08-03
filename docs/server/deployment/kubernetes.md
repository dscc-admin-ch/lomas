# Kubernetes Deployment via Helm

We provide a Helm chart for deploying Lomas on a Kubernetes cluster. The chart is mainly developped for vanilla Kubernetes clusters but we also include some adaptations for RedHat Openshift clusters.

## Prerequisites

Before you begin, make sure you have the following:

1. __Kubernetes Cluster__: A running Kubernetes cluster.
    If you don't have one, you can set up a local cluster using Minikube
    or Kind, or use a cloud provider like GKE, EKS, or AKS.
2. __Helm__: Helm installed on your local machine.
    Follow the [official Helm installation guide](https://helm.sh/docs/intro/install/)
    if you haven't installed Helm yet.
3. __kubectl__: Kubernetes command-line tool ``kubectl``
    installed and configured to communicate with your cluster.
    You can install ``kubectl`` by following the
    [official Kubernetes installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl/).

## Minimal deployment

The following outlines the steps required for a basic deployment:

1. __Download the Helm chart:__ If deploying a released version of Lomas use
  ```sh
  helm repo add lomas https://dscc-admin-ch.github.io/helm-charts
  ```
  The source code for the chart can be found in the project repository under `deploy/charts/lomas/`.

2. __Download the values file:__ Download the values file using
  ```sh
  helm show values lomas/lomas-server > values.yaml
  ```
  Alternatively, copy the file from `deploy/charts/lomas/values.yaml` in the project repository.
3. __Update the values file:__ You need to update at least the following urls for the chart to work:
    - `server.runtime_args.server.authenticator.oidc_discovery_url`, set this to your IdP's discovery url, or Dex's if enabled.
    - `server.ingress.hostname`: Choose a hostname supported by your cluster.
    - `demoSetupJob.config.serverUrl`: Set this to the server hostname.
    - `dashboard.streamlitServerSecrets`: Set the `redirectUri`s address to the dashboard ingress and the `serverMetadataUrl` to your IdP's discovery endpoint.
    - `dashboard.ingress.hostname`: Choose a hostname supported by your cluster.
    - `dex.ingress.hosts.host`: Choose a hostname supported by your cluster. Reminder, Dex is only included for testing purposes, do not use in production!
4. __Install the chart:__ Run
    ```.sh
  helm install lomas-sever lomas/lomas-server -f values.yaml
  ```
5. The chart's post-installation notes will show the server and dashboard urls. You can continue to the [administration section](../administration/index.md) for how to administer your Lomas instance.

## Kubernetes Secret Management

When deploying through the Helm chart, various secret values (e.g. credentials) are injected into Lomas containers at runtime.
In Kubernetes, secret values are stored separately and managed through a dedicated resource: Secrets.
Secret values are either provided to the Lomas chart directly via the values.yaml file (for testing purposes) or preferably via existing Kubernetes secrets.
The secret format is sometimes enforced by the underlying charts Lomas depends on. Here is a list of all secret resources used/created by the Lomas chart.


- __Server bootstrap credential__
    - Existing secret: `server.runtime_args.bootstrap.existingSecret` and `..existingkey`.
    - Setting the value: `server.runtime_args.bootstrap.value`.
- __Admin dashboard__
    - Streamlit requires a secret file in TOML format for getting information related to authentication.
    - Existing secret: `dashboard.streamlitServerSecrets.existingSecret` and `..existingSecretKey`.
    - `dashboard.streamlitServerSecrets.value` is used to set the value directly.
- __Private DB Credentials__
    - Credentials for external private databases are read by the Lomas server and worker through their conf*igs and thus also injected as environment variables via Kubernetes secrets.
    - For each set of credentials to a private database, one can either specify an existing secret or set the credentials as an element of the list at ``server.runtime_args.private_db_credentials``.
    - Existing secret: Add the name of the existing secret as an element of the list by adding ``existing_secret: <name of your secret>`` to the ``private_db_credentials`` list. The secret key should be ``private-db-credentials`` and contain a valid json representation of the private database credentials.
    - Values file: Directly add the dictionary representing the credentials as an element of the ``private_db_credentials`` list.
