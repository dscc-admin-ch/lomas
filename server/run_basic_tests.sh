#!/bin/bash

cd ../core
export PYTHONPATH=$(pwd):$PYTHONPATH

cd ../server/
export PYTHONPATH=$(pwd):$PYTHONPATH

cd lomas_server/
python -m unittest discover -s .
ret=$?
cd ..

exit $ret