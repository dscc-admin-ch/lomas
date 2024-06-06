#!/bin/bash

cd ./lomas_server
python --source=. -m unittest discover -s .
ret=$?
cd ..

exit $ret