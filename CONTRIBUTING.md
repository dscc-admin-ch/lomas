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

Settings up the environment with [devenv](https://devenv.sh/):

1. `sh <(curl -L https://nixos.org/nix/install) --daemon --no-channel-add --nix-extra-conf-file <(echo -e "experimental-features = nix-command flakes \ntrusted-users = root ${USER:-}")`
2. `nix profile install nixpkgs#devenv`
3. (Optional) [automatic shell activation](https://devenv.sh/automatic-shell-activation/)
    1. Vscode: [direnv extension](https://marketplace.visualstudio.com/items?itemName=mkhl.direnv)


Once in lomas repo: `devenv shell`

To spin-up necessary services: `devenv processes up`

Some utilities are provided inside the environment such as:

- `run-linter` will run all the Linting suit (isort/black/flake8/pylint/pydocstringformatter/mypy)
- `ut` runs the server pytest suit
- `ut-coverage` runs the server coverage & report generation

Note that some of them (fast enough) are integrated as git pre-commit hook (namely isort/black/flake8/pylint)


## Linting and Other Checks

To ensure code quality and consistency, we perform several checks using various tools. Below is a list of the checks that should be performed:

- **Code Formatting:** Use `black` to automatically format the code. In `lomas/server/lomas_server`, `lomas/client/lomas_client` and `lomas/core/lomas_core`:
  ```bash
  black .
  ```

- **Code Style and Static Analysis**: Use flake8 to verify formatting and perform static code analysis. In `lomas/server/lomas_server` , `lomas/client/lomas_client` and `lomas/core/lomas_core`:
 ```bash
  flake8 .
  ```

- **Static Type Checking**: Use mypy for static type checking. Note that both the server and the client have their own mypi.ini files to ignore specific warnings. In `lomas/server`, `lomas/client` and `lomas/core`:
 ```bash
  mypy .
  ```

- **Additional Static Analysis**: Use pylint for further static analysis. Note that both the server and the client have their own .pylintrc files to ignore specific warnings. In `lomas/server/lomas_server`, `lomas/client/lomas_client` and `lomas/core/lomas_core`:
 ```bash
  pylint .
  ```

- **Automatic docstring linter formatting**: Use pydocstringformatter for automatically formatting docstring following PEP257 recommandations. In `lomas/server/lomas_server`, `lomas/client/lomas_client` and `lomas/core/lomas_core`:
 ```bash
  pydocstringformatter .
  ```

To streamline the process, you can use the `run_linter.sh` script in ``lomas`. The first time you run this script, use the following command to install dependencies:
```bash
chmod +x run_linter.sh
./run_linter.sh  --install-deps
```
For subsequent runs, to run all linters (on server, client and core) simply execute:
```bash
./run_linter.sh
```
To run the linter in a specific package, the package can be specified as argument:
```bash
./run_linter.sh --client
```
will only run the linter for the client. And similarly for `./run_linter.sh --core` and `./run_linter.sh --server`.

There should be no error or warning, otherwise the linting github action will fail. All configurations are in `lomas/server/pyproject.toml` and `lomas/client/pyproject.toml`.

As detailed below, we rely on GitHub workflows to automatically run these checks on pull requests, ensuring consistency and quality across all contributions.

## GitHub Workflows

This project uses a number of GitHub workflows to automate various CI/CD tasks. These task can also be manually run in a local environment during development. Please refer to the workflow files in `.github/workflows/` for further details.
The table below gives an overview of which workflows are triggered by what events.

| Workflow / Trigger     | PR to develop | PR to master | Push to develop | Push to release/** | Push to master | GitHub release |
|------------------------|---------------|--------------|-----------------|--------------------|----------------|----------------|
| Tests and Linters      | Yes           | Yes          | No              | No                 | No             | No             |
| Docker build and push  | No            | No           | Yes (tag = git sha) | No             | Yes (tag = git sha) | Yes (tags = latest and semver (x.y.z)) |
| Client library push    | No            | No           | No              | No                 | No             | Yes (must manually adjust version) |
| Helm charts push       | No            | No           | No              | Yes (must manually adjust version)  | No             | No             |
| Documentation push     | No            | No           | Yes (for latest)| No                 | No             | Yes (for stable, must manually add version) |
| Security with CodeQL*  | Yes           | Yes          | No              | No                 | No             | No             |

Of these workflows, three of them need manual intervention to adjust the version number:

* **Client library push**: The 'version' and the 'install_requires' must be set in `core/setup.py`, `server/setup.py` and `client/setup.py` ('install_requires' should match the list of library in requirements.txt and the new version of `core`).
* **Helm chart push**: The chart version (`version`) and app version (`AppVersion`) of the server and the client must be updated in `server/deploy/helm/charts/lomas_server/Chart.yml`and `client/deploy/helm/charts/lomas_client/Chart.yaml`.
* **Documentation push**: If a new version is released, it must be added to the `docs/versions.yaml` file. For more details on the generation of the documentation, please refer to `docs` and the `docs/build_docs.py` script.

*The Security with CodeQL workflow is also triggered every Monday at 9am.


## Release Workflow

The following actions must take place in this order when preparing a new release:

1. Create a `release/vx.y.z` branch from develop.
2. Fix remaining issues.
3. Adjust versions for the client, core and server libraries (in the different setup.py), the helm charts, as well as for the documentation.
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
