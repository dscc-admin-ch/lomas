#!/bin/bash

docker compose -f docker-compose-test.yml up --detach

sleep 3

cd ./src
export LOMAS_TEST_MONGO_INTEGRATION=1
python -m unittest discover -s .
cd ..

docker compose -f docker-compose-test.yml down --volumes