Git and Release Workflow
=========================

When preparing a new release, developers must take care to correctly follow the release process.

Git Branches
--------------

* **master**: This is the stable branch. Release tags are always on this branch and the latest release is always the head of this branch.
* **develop**: This is the main development branch and can be ahead of the master branch.
  One should never directly merge and push to develop but perform a pull request on GitHub.
  The PR can only be merged if approved by another developer and all automatic tests pass.
* **wip_xx**: Feature branches for feature number xx start with wip_xx (one can add a short name to the branch name).
  They always branch off develop, and as explained above, are merged to develop via GitHub pull requests.
* **release/vx.y.z**: These are release branches (for version vx.y.z). They always branch off from develop.
  Once the release process is complete (see below), the release branch is merged to both master and develop via GitHub pull requests.

GitHub Workflows
-----------------

This project uses a number of GitHub workflows to automate various CI/CD tasks.
The table bellow gives an overview of which workflows are triggered by what events.

.. list-table:: Main GitHub Workflows Summary
    :widths: 2 1 1 1 1 1 1
    :header-rows: 1
    :stub-columns: 1

    * - Worflow / Trigger
      - PR to develop
      - PR to master
      - Push to develop
      - Push to release/**
      - Push to master
      - GitHub release
    * - Tests and Linters
      - Yes
      - Yes
      - No
      - No
      - No
      - No
    * - Docker build and push
      - No
      - No
      - Yes (tags git sha)
      - No
      - Yes (tags git sha)
      - Yes (tags latest and semver)
    * - Client library push
      - No
      - No
      - No
      - No
      - No
      - Yes (must manually adjust version)
    * - Helm charts push
      - No
      - No
      - No
      - Yes (must manually adjust version)
      - No
      - No
    * - Documentation push
      - No
      - No
      - Yes
      - No
      - No
      - Yes (must manually add version)

Of these worflows, three of them need manual intervention to adjust the version number:

* **Client library push**: The version must be set in "client/setup.py"
* **Helm chart push**: The app version and chart version must be updated in "server/deploy/helm/charts/lomas_server/Chart.yml"
* **Documentation push**: If a new version is released, it must be added to the "docs/versions.yaml" file.
    
Release Workflow
-----------------

The following actions must take place in this order when preparing a new release:

#. Create a release/vx.y.z branch from develop.
#. Fix remaining issues.
#. Adjust versions for the client library, the helm charts, as well as for the documentation.
#. Create a GitHub PR from this branch to develop AND master (make sure you are up to date with develop by rebasing on it)
#. Once merged, manually create a release on GitHub with the tag "vx.y.z".

The workflows listed in the previous section will take care of building and publishing the different items (docker images, pip packages, etc.).


