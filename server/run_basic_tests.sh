#!/bin/bash

cd ./lomas_server
python -m unittest discover -s .
ret=$?
cd ..

exit $ret