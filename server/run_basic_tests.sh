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
pytest ./administration/tests/test_streamlit_app_page_b.py
ret3=$?
cd ..

ret=$((ret1 + ret2 + ret3))
exit $ret