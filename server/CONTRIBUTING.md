# Notes for Server Contributors

## Tests

It is possible to test the server without an mongodb administration database. One can do so by executing the `run_basic_tests.sh` script. Make sure to have an activated python venv in a linux environment with the server requirements installed for it to work.

It is also possible to test the server with standard tests or integration tests (for the mongodb).
The `run_tests_and_converage.sh` script runs the integration tests. Again, make sure to have an activated python venv in a linux environment with the server requirements installed for it to work.

Local tests can also (except for those using the mongodb_admin) can be run with a simple `python -m unittest discover -s . ` from the `lomas_server` directory. The tests will be based on the config in `lomas/server/lomas_server/tests/test_configs/test_config.yaml` and be executed with the AdminYamlDatabase. 

Tests are also automatically run in GitHub workflows during different events (pull requests, pushes, etc.). Please refer to the general notes for contributors for more informations.
