# Tips for developers

It is recommended to run the project with python 3.11.

## Start service

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

It is possible to test the server with standard tests or integration tests (for the mongodb).
The `run_integration_tests.sh` script runs the integration tests, make sure to have an activated python venv in a linux environment with the server requirements installed for it to work.

Local tests (except for those using the mongodb_admin) can be run with a simple `python -m unittest discover -s . ` from the `lomas_server` directory. The tests will be based on the config in `lomas/server/lomas_server/tests/test_configs/test_config.yaml` and be executed with the AdminYamlDatabase. 
For local tests on the mongodb_admin, first get in the container with `docker exec -it lomas_server_dev bash` and then run the tests.


A github workflow is configured to run the integration tests script for pull requests on the develop and master branches.

## Linting and other checks

Here is a list of the checks performed:

    - Use black to automatically format the code: `black .`
    - Use flake to verify formating and performing a static code analysis: `flake8 .`
    - Use mypy for static type checking: `mypy .`
    - Use pylint for further static analysis: `pylint --disable=E0401 --disable=C0114 --disable=C0301 --disable=R0903 --disable=E0611 --disable=W0621 --disable=R0915 --disable=E0606 .`
    
        - `disable=E0401` to ignore import-error (false positive)
        - `disable=C0114` to ignore missing-module-docstring (don't think it is necessary)
        - `disable=R0903` to ignore too-few-public-methods (maybe refactor ?)
        - `disable=C0301` to ignore line-too-long (already handled by flake8)
        - `disable=E0611` to ignore no-name-in-module (false positive)
        - `disable=W0621` to ignore redefined-outer-name (in app.py)
        - `disable=R0915` to ignore too-many-statements (in app.py)
        - `disable=E0606` to ignore possibly-used-before-assignment
        
We rely on a github workflow to automatically run the checks on pull requests.

## Documentation

Documentation is automatically generated from the code docstrings with sphinx, as well as the resulting html pages.
The process goes in two steps
    - `sphinx-apidoc -o ./docs/source ./lomas_server` for generating the .rst files.
    - `make html` from the `./docs` folder to generate the webpages.

We do not check the documentation files into the repo, but rather rely on a github workflow to generate and publish it 
on a dedicated repo's github pages for easy access from the web.
