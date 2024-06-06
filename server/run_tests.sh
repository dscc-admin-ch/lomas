#!/bin/bash

cd ./lomas_server
coverage run --source=. -m unittest discover -s .
ret=$?
cd ..

exit $ret