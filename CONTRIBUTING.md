# Notes for Contributors

This page gives general information about developer workflows valid for the entire project. For more specific information about developing for the client or server
part of the project, refer to:
* Stable version of the [client contributor notes](https://dscc-admin-ch.github.io/lomas-docs/CONTRIBUTING_CLIENT.html) (or in the [GitHub repo](https://github.com/dscc-admin-ch/lomas/blob/master/client/CONTRIBUTING.md))
* Stable version of the [server contributor notes](https://dscc-admin-ch.github.io/lomas-docs/CONTRIBUTING_SERVER.html) (or in the [GitHub repo](https://github.com/dscc-admin-ch/lomas/blob/master/server/CONTRIBUTING.md))

## Git Branches

* **master**: This is the stable branch. Release tags are always on this branch and the latest release is always the head of this branch.
* **develop**: This is the main development branch and can be ahead of the master branch.
  One should never directly merge and push to develop but perform a pull request on GitHub.
  The PR can only be merged if approved by another developer and all automatic tests pass.
* **wip_xx**: Feature branches for feature number xx start with wip_xx (one can add a short name to the branch name).
  They always branch off develop, and as explained above, are merged to develop via GitHub pull requests.
* **release/vx.y.z**: These are release branches (for version vx.y.z). They always branch off from develop.
  Once the release process is complete (see below), the release branch is merged to both master and develop via GitHub pull requests.

## Devenv

Setting up the environment with [devenv](https://devenv.sh/):

1. `./scripts/bootstrap.sh`
2. `nix profile install nixpkgs#{dev,dir}env`
3. (Optional) [automatic shell activation](https://devenv.sh/automatic-shell-activation/)
    1. add `echo 'eval "$(direnv hook bash)"' >> ~/.bashrc` [direnv shell hook](https://direnv.net/docs/hook.html)
    2. Approve (once) inside the cloned directory / vscode terminal: `direnv allow`
    3. Install vscode extension: [mkhl.direnv](https://marketplace.visualstudio.com/items?itemName=mkhl.direnv)


Once in lomas repo run the following to activate the devenv: `devenv shell`.

The following utilities are now available in your shell:
- `yelp` will print a similar help page.
- `devenv up` will start up the environment (lomas server, worker, keycloak, mongodb, rabbitmq) and set up the components. Demo users and datasets will also be added to the service.
- `devenv up -- --namespace=telemetry` or `process-compose up` will do the same as above but with telemetry enabled.
- `yq $PC_CONFIG_FILES` will show what process-compose is doing.
- `ut / pytest -k <name of your test>` will run individual tests, no need to setup the python path. If your tests require the services to be up, run `devenv up` before.
- `ut-coverage` will run tests and coverage.
- `uv sync --all-extras [-U]` will fix broken/out of sync/missing packages.
- `uv add <packages>` will add new packages.
- `run-linter` will run all the Linting suit (black/ruff/pylint/pydocstringformatter/mypy)
- `build-docs` builds all version of the docs (requires `uv sync --all-extras` first)
- `build-docs-local` builds the local version of the doc (requires `uv sync --all-extras` first), the htlm will open automatically.


Note that some of the utilities (fast enough) are integrated as git pre-commit hook (namely black/ruff/pylint).

## Python package management

We use [`uv`](https://docs.astral.sh/uv/reference/cli/) for managing Python dependencies and package builds. The repo is setup using the workspaces layout, see [here for reference](https://docs.astral.sh/uv/concepts/projects/workspaces/).

Here are some of the more common commands:
- `uv sync` syncs the virtual environment with the uv.lock file. This also removes installed packages that are not listed in that file.
- `uv sync --all-extras` does the same as above but with all extra dependencies.
- `uv add <package>` adds a package to the project. The pyproject.toml file as well as the uv.lock file are updated.

Activating the devenv already activates the python venv with uv.


## Linting and Other Checks

To ensure code quality and consistency, we perform several checks using various tools. Below is a list of the checks that are performed by the `run-linter` command:

- **Code Formatting:** We use `black` to automatically format the code.
- **Code Style and Static Analysis**: We use ruff to verify formatting and perform static code.
- **Static Type Checking**: We use mypy for static type checking. Note that both the server and the client have their own pyproject.toml files with configs to ignore specific warnings.
- **Additional Static Analysis**: We use pylint for further static analysis. Note that both the server and the client have their own config in their respective pyproject.toml files to ignore specific warnings.
- **Automatic docstring linter formatting**: We use pydocstringformatter for automatically formatting docstring following PEP257 recommandations.
- **Import statement reordering**: We use ruff to perform this task.

There should be no error or warning when calling `run-linter`, otherwise the linting github action will fail. All configurations are in

* `lomas/pyproject.toml`
* `lomas/core/pyproject.toml`
* `lomas/server/pyproject.toml`
* `lomas/client/pyproject.toml`.

As detailed below, we rely on GitHub workflows to automatically run these checks on pull requests, ensuring consistency and quality across all contributions.

## GitHub Workflows

This project uses a number of GitHub workflows to automate various CI/CD tasks. These task can also be manually run in a local environment during development. Please refer to the workflow files in `.github/workflows/` for further details.
The table below gives an overview of which workflows are triggered by what events.

| Workflow / Trigger     | PR to develop | PR to master | Push to develop | Push to release/** | Push to master | GitHub release |
|------------------------|---------------|--------------|-----------------|--------------------|----------------|----------------|
| Tests and Linters      | Yes           | Yes          | No              | No                 | No             | No             |
| Docker build and push  | Yes (no push) | Yes (no push)| Yes (tag = git sha) | No             | Yes (tag = git sha) | Yes (tags = latest and semver (x.y.z)) |
| Python libraries push  | No            | No           | No              | No                 | No             | Yes (must manually adjust version) |
| Helm charts push       | No            | No           | No              | Yes (must manually adjust version)  | No             | No             |
| Documentation push     | No            | No           | Yes (for latest)| No                 | No             | Yes (for stable, must manually add version) |
| Security with CodeQL*  | Yes           | Yes          | No              | No                 | No             | No             |

Of these workflows, three of them need manual intervention to adjust the version number:

* **Python libraries push**: The 'version' and the 'install_requires' must be set in `core/pyproject.toml`, `server/pyproject.toml` and `client/pyproject.toml` ('install_requires' should match the list of library in requirements.txt and the new version of `core`).
* **Helm chart push**: The chart version (`version`) and app version (`AppVersion`) of the server and the client must be updated in `server/deploy/helm/charts/lomas_server/Chart.yml`and `client/deploy/helm/charts/lomas_client/Chart.yaml`.
* **Documentation push**: If a new version is released, it must be added to the `docs/versions.yaml` file. For more details on the generation of the documentation, please refer to `docs` and the `docs/build_docs.py` script.

*The Security with CodeQL workflow is also triggered every Monday at 9am.


## Release Workflow

The following actions must take place in this order when preparing a new release:

1. Create a `release/vx.y.z` branch from develop.
2. Fix remaining issues.
3. Adjust versions for the client, core and server libraries (in the different pyproject.toml), the helm charts, as well as for the documentation.
4. Create a GitHub PR from this branch to develop AND master (make sure you are up to date with develop by rebasing on it)
5. Once merged, manually create a release on GitHub with the tag `vx.y.z`.

The workflows listed in the previous section will take care of building and publishing the different items (docker images, pip packages, etc.).

Note: Helm charts are updated when there is a push on the `release/vx.y.z` branch. If you have a specific deployment that rely on the Chart, you can test it before finishing the release. Then, **do not forget** to update the chart and app versions of your specific deployment.

## Adding a DP Library

It is possible to add DP libraries quite seamlessly. Let's say the new library is named 'NewLibrary'
Steps:
0. Add the necessary requirements in `lomas/lomas_server/requirements.txt` and `lomas/lomas_client/requirements.txt`
1. Add the library the the `DPLibraries` StrEnum class in `lomas/lomas_core/constants.py` (`DPLibraries.NEW_LIBRARY = "new_library"`) and add the `NewLibraryQuerier` option in the `querier_factory` (in  `lomas/lomas_server/dp_queries/dp_libraries/factory.py`).
2. Create a file for your querier in the folder `lomas/lomas_server/dp_queries/dp_libraries/new_library.py`. Inside, create a class `NewLibraryQuerier` that inherits from `DPQuerier` (`lomas/lomas_server/dp_queries/dp_querier.py`), your class must contain a `cost` method that return the cost of a query and a `query` method that return a result of a DP query.
3. Add the three associated API endpoints .
- a. Add the endpoint handlers in `lomas/lomas_server/routes/routes_dp.py`: `/new_library_query` (for queries on the real dataset), `/dummy_new_library_query` (for queries on the dummy dataset) and `/estimate_new_library_cost` (for estimating the privacy budget cost of a query).
- b. The endpoints should have predefined pydantic BaselModel types. Aadd BaseModel classes of expected input `NewLibraryModel`, `DummyNewLibraryModel`, `NewLibraryCostModel` in  `lomas/lomas_server/utils/query_models.py` and add the request case in the function `model_input_to_lib()`.
- c. The endpoints should have predefined default values `example_new_library`, `example_dummy_new_library` in  `lomas/lomas_server/utils/query_examples.py`.
4. Add tests in `lomas/lomas_server/tests/test_new_library.py` to test all functionnalities and options of the new library.
5. Add the associated method in `lomas-client` library in `lomas/client/lomas_client/client.py`. In this case there should be `new_library_query` for queries on the private and on the dummy datasets and `estimate_new_library_cost` to estimate the cost of a query.
6. Add a notebook `Demo_Client_Notebook_NewLibrary.ipynb` in `lomas/client/notebook/` to give example of the use of the library.

### External Loggers
Some libraries have 'custom object' parameters which are not readily serialisable.
In those cases, a `logger` library can be made to serialise the object in the client (before sending them to the server via FastAPI) and then deserialise them in their `DPQuerier` class in the server.

Some examples are avalaible here:
- `opendp_logger` for opendp pipelines: https://github.com/opendp/opendp-logger
- `diffprivlib_logger` for diffprivlib pipelines: https://github.com/dscc-admin-ch/diffprivlib-logger
- `smartnoise_synth_logger` for smartnoise_synth table transformer constraints: https://github.com/dscc-admin-ch/smartnoise-synth-logger

Do not forget to add these libraries in the `requirements.txt` files.

## Adding a Data Connector (for private dataset in various databases)
Here is the explanation of how to add a new data connector named `NewDataConnector` for the example.

1. Add the new dataset store to the `NewDataConnector` StrEnum class in `lomas/lomas_server/constants.py`.
2. Add the `NewDataConnector` option in the `data_connector_factory` function (in `lomas/lomas_server/data_connector/factory.py`).
3. Create a file for your dataset store in the folder `lomas/lomas_server/data_connector/new_data_connector.py`. Inside, create a class `NewDataConnector` that inherits from `DataConnector` (`lomas/lomas_server/data_connector/data_connector.py`), your class must contain a `get_pandas_df` method that return a dataframe of the dataset.
4. Add tests in `lomas/lomas_server/tests/` to test all functionnalities of the new data connector.
