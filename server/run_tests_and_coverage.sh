#!/bin/bash

docker compose -f docker-compose-test.yml up --detach

sleep 3

cd ./lomas_server

# On admin_database: "mongodb" and dataset_store: "LRU_cache"
export LOMAS_TEST_MONGO_INTEGRATION=1
coverage run --source=. -m unittest discover -s .
ret=$?

# On admin_database: "yaml" and dataset_store: "basic"
export LOMAS_TEST_MONGO_INTEGRATION=0
coverage run -a --source=. -m unittest discover -s .
ret=$?

coverage report
coverage xml -o coverage.xml

cd ..

docker compose -f docker-compose-test.yml down --volumes

exit $ret