#!/bin/bash

cd ./lomas_server
coverage run --rcfile=<(echo "[run]\nrelative_files = True") --source=. -m unittest discover -s .
ret=$?
coverage report
coverage xml -o coverage.xml
cd ..

exit $ret