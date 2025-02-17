#!/bin/bash

cd ../core
export PYTHONPATH=$(pwd):$PYTHONPATH

cd ../server/
export PYTHONPATH=$(pwd):$PYTHONPATH

cd lomas_server/
python -m unittest discover -s .
ret1=$?
pytest ./administration/tests/test_streamlit_app.py
ret2=$?
# We disable these until we have a devenv with keycloak and a mongodb running
# so that we don't have to mock every function. TODO issue #405
#pytest ./administration/tests/test_streamlit_app_page_b.py
#ret3=$?
ret3=0
cd ..

ret=$((ret1 + ret2 + ret3))
exit $ret