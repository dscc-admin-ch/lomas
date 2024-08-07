#!/bin/bash

docker kill $(docker ps -a -q)
docker image rm gsc-ratls-test gsc-ratls-test-unsigned:latest ratls-test:latest

docker build --target sdd_private_session_prod -t ratls-test .

cd gsc-configs/gsc/

./gsc build -c ../config.yaml --rm ratls-test ../private-session.manifest

./gsc sign-image -c ../config.yaml  ratls-test /home/azureuser/.config/gramine/enclave-key.pem

./gsc info-image gsc-ratls-test

cd ../../