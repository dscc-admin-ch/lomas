# Notes for Server Contributors

It is recommended to run the project with python 3.11.

## Starting the Service

The different notebooks in `./notebooks` provide more complete documentation regarding the set up and administration of the server.

### On local machine
To start the container on a local machine, first create a mondodb volume
with `docker volume create mongodata`, then go to `lomas/server/` and run `docker compose up`. 
If you encounter any issue, you might want to run `docker compose down` first.

#### Additional services
Running `docker compose up` will also start two additional services automatically:
- a jupyter notebook environment that will be available at the address http://127.0.0.1:8888/ to interact as a user with the server
- a streamlit application that will be available at the address http://localhost:8501/ to interact with the server and the administration database as an administrator.

### On a kubernetes cluster
To start the server on a kubernetes cluster, first add the repo with:
`helm repo add lomas https://dscc-admin-ch.github.io/helm-charts`
and then install the chart with:
`helm install lomas-sever lomas/lomas-server`

### On Onyxia
To start the server on Onyxia, select the `lomas `service, (optionnally adapt the administration and runtime parameters) and click on 'Lancer'.

## Tests

It is possible to test the server without an mongodb administration database. One can do so by executing the `run_basic_tests.sh` script. Make sure to have an activated python venv in a linux environment with the server requirements installed for it to work.

It is also possible to test the server with standard tests or integration tests (for the mongodb).
The `run_tests_and_converage.sh` script runs the integration tests. Again, make sure to have an activated python venv in a linux environment with the server requirements installed for it to work.

Local tests can also (except for those using the mongodb_admin) can be run with a simple `python -m unittest discover -s . ` from the `lomas_server` directory. The tests will be based on the config in `lomas/server/lomas_server/tests/test_configs/test_config.yaml` and be executed with the AdminYamlDatabase. 

Tests are also automatically run in GitHub workflows during different events (pull requests, pushes, etc.). Please refer to the general notes for contributors for more informations.
