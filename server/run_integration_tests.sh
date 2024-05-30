#!/bin/bash

docker compose -f docker-compose-test.yml up --detach

sleep 5

cd ./lomas_server
export LOMAS_TEST_MONGO_INTEGRATION=1
python -m unittest discover -s .
ret=$?
cd ..

docker compose -f docker-compose-test.yml down --volumes

exit $ret