#!/bin/bash

docker compose -f docker-compose-test.yml up --detach

sleep 15

cd ../core
export PYTHONPATH=$(pwd):$PYTHONPATH

cd ../server/
export PYTHONPATH=$(pwd):$PYTHONPATH

cd lomas_server/

python ./worker.py &

# "mongodb", "LRU_cache", production mode, "jitter"
pytest --cov .
ret=$?

coverage report
coverage xml -o coverage.xml

cd ..

docker compose -f docker-compose-test.yml down --volumes

exit $ret
