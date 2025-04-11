# Notes for Server Contributors

## Tests
Tests are automatically run in GitHub workflows during different events (pull requests, pushes, etc.). Please refer to the general notes for contributors for more informations.

The test suite relies on certain services to be up (with `devenv up`) and is run with `ut-coverage`.

Individual tests can directly be run from the devenv environnent with `pytest -k <keyword expression>`, this without having to set the python path or any other configuration.

### Deprecated
It is also possible to test the server with the test docker compose file instead of starting devenv's process-compose.
The `run_tests_and_converage.sh` script runs the integration tests. Again, make sure to have an activated python venv in a linux environment with the server requirements installed for it to work or install and activate the devenv.


