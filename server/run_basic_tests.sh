#!/bin/bash

cd ../core
export PYTHONPATH=$(pwd):$PYTHONPATH

cd ../server/
export PYTHONPATH=$(pwd):$PYTHONPATH

cd lomas_server/
python -m unittest discover -s .
ret=$?
pytest ./administration/tests/test_streamlit_app.py
pytest ./administration/tests/test_streamlit_app_b.py
cd ..

exit $ret