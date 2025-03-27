#!/bin/bash

docker compose -f docker-compose-test.yml --env-file ./configs/.env.docker-compose up --detach

sleep 15

cd ../core
export PYTHONPATH=$(pwd):$PYTHONPATH

cd ../server/
export PYTHONPATH=$(pwd):$PYTHONPATH

cd lomas_server/

export LOMAS_CONFIG_PATH="tests/test_configs/test_config_mongo.yaml"
export LOMAS_SECRETS_PATH="tests/test_configs/test_secrets.yaml"
python ./worker.py &

# "mongodb", "LRU_cache", production mode, "jitter"
pytest --cov .
ret=$?

coverage report
coverage xml -o coverage.xml

cd ..

docker compose -f docker-compose-test.yml --env-file ./configs/.env.docker-compose up down --volumes

exit $ret
