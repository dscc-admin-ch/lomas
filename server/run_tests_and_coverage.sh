#!/bin/bash

docker compose -f docker-compose-test.yml up --detach

sleep 15

cd ../core/lomas_core
export PYTHONPATH=$(pwd)/..:$PYTHONPATH

cd ../../server/lomas_server
export PYTHONPATH=$(pwd)/..:$PYTHONPATH

# "mongodb", "LRU_cache", production mode, "jitter"
export LOMAS_TEST_MONGO_INTEGRATION=1 # tests with mongodb available
export LOMAS_TEST_S3_INTEGRATION=1 # tests with s3 minio available
coverage run --source=. -m unittest discover -s .
ret1=$?

# "yaml", "basic", developer mode, "stall"
export LOMAS_TEST_MONGO_INTEGRATION=0
export LOMAS_TEST_S3_INTEGRATION=0
coverage run -a --source=. -m unittest discover -s .
ret2=$?

coverage report
coverage xml -o coverage.xml

cd ..

docker compose -f docker-compose-test.yml down --volumes

ret=$((ret1 + ret2))
exit $ret