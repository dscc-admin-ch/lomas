# Contributing to Lomas

This page gives general information about developer workflows in the Lomas project.

## Git Branches

* **master**: This is the stable branch. Release tags are always on this branch and the latest release is always the head of this branch.
* **develop**: This is the main development branch and can be ahead of the master branch.
  One should never directly merge and push to develop but perform a pull request on GitHub.
  The PR can only be merged if approved by another developer and all automatic tests pass.
* **wip_xx**: Feature branches for feature number xx start with wip_xx (one can add a short name to the branch name).
  They always branch off from develop, and as explained above, are merged to develop via GitHub pull requests.
* **release/vx.y.z**: These are release branches (for version vx.y.z). They always branch off from develop.
  Once the release process is complete (see below), the release branch is merged to both master and develop via GitHub pull requests.

## Devenv

We use [devenv](https://devenv.sh/) devenv to setup our development environent. You can run the following steps to install nix and devenv:

1. `./scripts/bootstrap.sh`
2. `nix profile add nixpkgs#{dev,dir}env`
3. (Optional) [automatic shell activation](https://devenv.sh/auto-activation/)
    1. add `echo 'eval "$(direnv hook bash)"' >> ~/.bashrc` [direnv shell hook](https://direnv.net/docs/hook.html)
    2. Approve (once) inside the cloned directory / vscode terminal: `direnv allow`
    3. Install vscode extension: [mkhl.direnv](https://marketplace.visualstudio.com/items?itemName=mkhl.direnv)


Once in lomas repo run the following to activate the devenv: `devenv shell`.
The following utilities are now available in your shell:

- `yelp` will print a similar help page.
- `devenv up` will start up the environment (lomas server, worker, dex, rabbitmq) and set up the components. Demo users and datasets can also be added to the service using `demo-setup`.
- `devenv -P telemetry up` will do the same as above but with telemetry enabled.
- `ut / pytest -k <name of your test>` will run individual tests, no need to setup the python path. If your tests require the services to be up, run `devenv up` before.
- `devenv -P coverage test` will run tests and coverage.
- `uv sync --all-extras [-U]` will fix broken/out of sync/missing packages.
- `uv add <packages>` will add new packages.
- `run-linter` will run all the Linting suit (ruff/pydocstringformatter/mypy)
- `build-docs` builds all version of the docs (requires `uv sync --all-extras` first)
- `build-docs-local` builds the local version of the doc (requires `uv sync --all-extras` first), the htlm will open automatically.


Note that some of the utilities (fast enough) are integrated as git pre-commit hook (namely ruff/pylint).

## Python package management

We use [`uv`](https://docs.astral.sh/uv/reference/cli/) for managing Python dependencies and package builds. The repo is setup using the workspaces layout, see [here for reference](https://docs.astral.sh/uv/concepts/projects/workspaces/).

Here are some of the more common commands:

- `uv sync` syncs the virtual environment with the uv.lock file. This also removes installed packages that are not listed in that file.
- `uv sync --all-extras` does the same as above but with all extra dependencies.
- `uv add <package>` adds a package to the project. The pyproject.toml file as well as the uv.lock file are updated. Move into the client/code/server repository to add the package to either one of these directly.
- `uv remove <package>` removes a package from the project.

Activating the devenv already activates the python venv with uv.

## Linting and Other Checks

To ensure code quality and consistency, we perform several checks using various tools. Below is a list of the checks that are performed by the `run-linter` command:

- **Code Formatting:** We use ruff to automatically format the code.
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

This project uses a number of GitHub workflows to automate various CI/CD tasks. These tasks can also be manually run in a local environment during development. Please refer to the workflow files in `.github/workflows/` for further details.
The table below gives an overview of which workflows are triggered by what events.

| Workflow / Trigger     | PR to develop | PR to master | Push to develop | Push to release/** | Push to master | GitHub release |
|------------------------|---------------|--------------|-----------------|--------------------|----------------|----------------|
| Tests and Linters      | Yes           | Yes          | No              | No                 | No             | No             |
| Docker build and push  | Yes (no push) | Yes (no push)| Yes (tag = git sha) | No             | Yes (tag = git sha) | Yes (tags = latest and semver (x.y.z)) |
| Python libraries push  | No            | No           | Yes             | No                 | No             | Yes (pre-version on tag, must manually adjust version) |
| Helm charts push       | No            | No           | No              | Yes (must manually adjust version)  | No             | No             |
| Documentation push     | No            | No           | Yes (for latest)| No                 | No             | Yes (for stable, must manually add version) |
| Security with CodeQL*  | Yes           | Yes          | No              | No                 | No             | No             |

Of these workflows, three of them need manual intervention to adjust the version number:

* **Python libraries push**: The `version` and the `install_requires` must be set in `core/pyproject.toml`, `server/pyproject.toml` and `client/pyproject.toml` ('install_requires' should match the list of library in requirements.txt and the new version of `core`).
* **Helm chart push**: The chart version (`version`) and app version (`AppVersion`) of the server and the client must be updated in `server/deploy/helm/charts/lomas_server/Chart.yml`and `client/deploy/helm/charts/lomas_client/Chart.yaml`.
* **Documentation push**: __TODO__ Mike setup

*The Security with CodeQL workflow is also triggered every Monday at 9am.

## Release Workflow

The following actions must take place in this order when preparing a new release:

1. Create a `release/vx.y.z` branch from develop.
2. Fix remaining issues.
3. Adjust versions for the client, core and server libraries (in the different pyproject.toml), the helm charts, as well as for the documentation.
4. Create a GitHub PR from this branch to develop AND master (make sure you are up to date with develop by rebasing on it)
5. Once merged, manually create a release on GitHub with the tag `vx.y.z`.

The workflows listed in the previous section will take care of building and publishing the different items (docker images, pip packages, etc.).

Note: Helm charts are updated when there is a push on the `release/vx.y.z` branch. If you have a specific deployment that relies on the Chart, you can test it before finishing the release. Then, **do not forget** to update the chart and app versions of your specific deployment.
