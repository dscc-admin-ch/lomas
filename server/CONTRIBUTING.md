# Tips for developers

## Start service

The different notebooks in `./notebooks` provide more complete documentation regarding the set up and administration of the server.
### On local machine
To start the container on a local machine, first create a mondodb volume
with `docker volume create mongodata`, then go to `lomas/server/` and run `docker compose up`. 
If you encounter any issue, you might want to run `docker compose down` first.

### On a kubernetes cluster
To start the server on a kubernetes cluster, first add the repo with:
`helm repo add lomas https://dscc-admin-ch.github.io/helm-charts`
and then install the chart with:
`helm install lomas-sever lomas/lomas-server`

### On Onyxia
To start the server on Onyxia, select the `lomas `service, (optionnally adapt the administration and runtime parameters) and click on 'Lancer'.

## Tests

It is possible to test the server with standard tests or integration tests (for the mongodb).
The `run_integration_tests.sh` script runs the integration tests, make sure to have an activated python venv
with the server requirements installed for it to work.

Local tests can be run with a simple `python -m unittest -s discover . ` from the `lomas_server` directory. The tests will be based on the config in `lomas/server/lomas_server/tests/test_configs/test_config.yaml` and be executed with the AdminYamlDatabase. 

A github workflow is configured to run the integration tests script for pull requests on the develop and master branches.

## Linting and other checks

Here is a list of the checks performed:
    - Use black to automatically format the code: `black .`
    - Use flake to verify formating and performing a static code analysis: `flake8 .`
    - Use mypy for static type checking: `mypy .`
    - Use pylint for further static analysis: `pylint . --disable=E0401 --disable=C0114 --disable=C0115 --disable=C0116 --disable=R0903 --disable=C0301`

We rely on a github workflow to automatically run the checks on pull requests.

## Documentation

Documentation is automatically generated from the code docstrings with sphinx, as well as the resulting html pages.
The process goes in two steps
    - `sphinx-apidoc -o ./docs/source ./lomas_server` for generating the .rst files.
    - `make html` from the `./docs` folder to generate the webpages.

We do not check the documentation files into the repo, but rather rely on a github workflow to generate and publish it 
on a dedicated repo's github pages for easy access from the web.
