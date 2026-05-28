# Devenv Test Deployment

This page provides instructions on how to run a local Lomas test instance.

!!! note

    This deployment method is meant for testing only and not safe for production!

    !!! warning "Prerequisites"

        Ensure you have cloned the repository and set up devenv as described in the [contributor's guide](../../concepts/contributing.md).

## Steps to Deploy Locally

1. To start a local instance, simply run `devenv up`.
2. To run the admin demo script which loads demo users and dataset into the database, run `lomas-demo-setup`. Make sure the server is ready before running this script.
3. Open one of the [example notebooks](../../client/index.md) to test the service. The environment variables for the client configuration are already present in the devenv environment. Parameters specific to the notebook user (e.g. Dr. Antartica) are set in the first few cells of each notebook. By default, demo notebooks use the client credentials flow. An IdP configured for production will not allow this flow, you can switch to the device authorizatoin flow by setting the `LOMAS_CLIENT_USER_PASSWORD` environment variable to false.
4. The server is available at `http://localhost:48080`. Bootstrap authorization is enabled by default, this allows to test API endpoints via swagger at `http://localhost:48080/docs`.
5. The admin dashboard is available at `http://localhost:8501/admin`. If the demo admin script was run, you can log in with the demo admin user (email: lomas_admin@example.com and password: lomas_admin).
6. Logs for all services started by devenv can be observed by navigating the manager started with the `devenv up` command. In adddition to those described above, they include RabbitMQ, Dex (IdP), Garage as well as two Lomas workers.


!!! info "__Note for Developers__"

    A Docker compose file also enables to start a local test environment.
    However, this method is only meant to test the Lomas OCI container images and some of the services (e.g. Garage) are not started/supported.
    The docker compose file is parametrized with an .env file via variable interpolation.
    We generate all configuration files using devenv before checking them into Git.
    This is specified with a note at the beginning of each of these automatically generated files.
