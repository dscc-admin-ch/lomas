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

## Linting and Other Checks

To ensure code quality and consistency, we perform several checks using various tools. Below is a list of the checks that should be performed:

- **Code Formatting:** Use `black` to automatically format the code. In `lomas/server/lomas_server` and `lomas/client/lomas_client`:
  ```bash
  black .
  ```

- **Code Style and Static Analysis**: Use flake8 to verify formatting and perform static code analysis. In `lomas/server/lomas_server` and `lomas/client/lomas_client`:
 ```bash
  flake8 .
  ```

- **Static Type Checking**: Use mypy for static type checking. Note that both the server and the client have their own mypi.ini files to ignore specific warnings. In `lomas/server` and `lomas/client`:
 ```bash
  mypy .
  ```

- **Additional Static Analysis**: Use pylint for further static analysis. Note that both the server and the client have their own .pylintrc files to ignore specific warnings. In `lomas/server/lomas_server` and `lomas/client/lomas_client`:
 ```bash
  pylint .
  ```

To streamline the process, you can use the `run_linter.sh` script in ``lomas`. The first time you run this script, use the following command to install dependencies:
```bash
chmod +x run_linter.sh
./run_linter.sh  --install-deps
```
For subsequent runs, simply execute:
```bash
./run_linter.sh
```

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

* **Client library push**: The version must be set in `client/setup.py`
* **Helm chart push**: The chart version (`version`) and app version (`AppVersion`) of the server and the client must be updated in `server/deploy/helm/charts/lomas_server/Chart.yml`and `client/deploy/helm/charts/lomas_client/Chart.yaml`.
* **Documentation push**: If a new version is released, it must be added to the `docs/versions.yaml` file. For more details on the generation of the documentation, please refer to `docs` and the `docs/build_docs.py` script.

*The Security with CodeQL workflow is also triggered every Monday at 9am.


## Release Workflow

The following actions must take place in this order when preparing a new release:

1. Create a `release/vx.y.z` branch from develop.
2. Fix remaining issues.
3. Adjust versions for the client library, the helm charts, as well as for the documentation.
4. Create a GitHub PR from this branch to develop AND master (make sure you are up to date with develop by rebasing on it)
5. Once merged, manually create a release on GitHub with the tag `vx.y.z`.

The workflows listed in the previous section will take care of building and publishing the different items (docker images, pip packages, etc.).

Note: Helm charts are updated when there is a push on the `release/vx.y.z` branch. If you have a specific deployment that rely on the Chart, you can test it before finishing the release. Then, do not forget to update the chart and app versions of your specific deployment.
