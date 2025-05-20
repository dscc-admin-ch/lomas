# Notes for Server Contributors

## Tests
Tests are automatically run in GitHub workflows during different events (pull requests, pushes, etc.). Please refer to the general notes for contributors for more informations.

The test suite relies on certain services to be up (with `devenv up`) and is run with `ut-coverage`.

Individual tests can directly be run from the devenv environnent with `pytest -k <keyword expression>`, this without having to set the python path or any other configuration.
