#!/bin/bash
# Default value for LOMAS_TEST_S3_INTEGRATION environment variable
LOMAS_TEST_S3_INTEGRATION=0
# Parse options
while getopts ":s" opt; do
  case ${opt} in
    s )
      LOMAS_TEST_S3_INTEGRATION=1
      ;;
    \? )
      echo "Invalid option: -$OPTARG" 1>&2
      exit 1
      ;;
  esac
done
# Shift the arguments to leave only the Python test files
shift $((OPTIND -1))
# Export the LOMAS_TEST_S3_INTEGRATION environment variable
export LOMAS_TEST_S3_INTEGRATION
docker compose -f docker-compose-test.yml up --detach

sleep 15

cd ./lomas_server


# "mongodb", "LRU_cache", production mode, "jitter"
export LOMAS_TEST_MONGO_INTEGRATION=1 # tests with mongodb available
python -m unittest tests."$@"
ret1=$?

cd ..

docker compose -f docker-compose-test.yml down --volumes

exit $ret1