# Tips for developpers

## Automatic documentation
If needed, install the sphinx package:
```
pip install sphinx
```

To automate the making of the documentation, in `lomas/client`, run:

```python
sphinx-build -M html documentation docs
```

To see the pages, go to `lomas/client/docs/html`, run:

```
start .\index.html
```
(in windows) and the doc page will open!

In Linux, you can use:
```
firefox ./index.html
```
## Push new version to Pypi
To push a new client library version on Pypi:
0. Verify the documentation and README.md are up to date
1. update the version in the setup of `lomas/client/setup.py`
2. delete `lomas/client/dist/` (if it exists)
3. In `lomas/client/` run `python setup.py sdist`
4. Then get the `PYPI_TOKEN` token and run `twine upload dist/* -u __token__ -p PYPI_TOKEN`
5. Got to [lomas](https://pypi.org/project/lomas-client/)  on PyPi to check the upload