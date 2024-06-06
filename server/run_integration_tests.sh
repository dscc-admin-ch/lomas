#!/bin/bash

docker compose -f docker-compose-test.yml up --detach

sleep 3

cd ./lomas_server

# On MongoDB Admin
export LOMAS_TEST_MONGO_INTEGRATION=1
coverage run --source=. -m unittest discover -s .
ret=$?

# On YamlDB Admin
export LOMAS_TEST_MONGO_INTEGRATION=0
coverage run -a --source=. -m unittest discover -s .
ret=$?

coverage report
coverage xml -o coverage.xml

cd ..

docker compose -f docker-compose-test.yml down --volumes

exit $ret