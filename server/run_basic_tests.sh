#!/bin/bash

cd ../core/lomas_core
export PYTHONPATH=$(pwd)/..:$PYTHONPATH

cd ../../server/lomas_server
export PYTHONPATH=$(pwd)/..:$PYTHONPATH
python -m unittest discover -s .
ret=$?
cd ..

exit $ret