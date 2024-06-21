# Notes for Client Contributors

## Pushing a new version to Pypi

This process is automated via a GitHub workflow. If one wishes to test the process, the following steps are needed:

0. Verify the documentation and README.md are up to date
1. update the version in the setup of `lomas/client/setup.py`
2. delete `lomas/client/dist/` (if it exists)
3. In `lomas/client/` run `python setup.py sdist`
4. Then get the `PYPI_TOKEN` token and run `twine upload dist/* -u __token__ -p PYPI_TOKEN`
5. Got to [lomas](https://pypi.org/project/lomas-client/)  on PyPi to check the upload