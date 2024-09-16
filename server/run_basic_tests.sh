#!/bin/bash

cd ./lomas_server
export PYTHONPATH=$(pwd)/..:$PYTHONPATH
python -m unittest discover -s .
ret=$?
cd ..

exit $ret