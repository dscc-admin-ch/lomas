docker build --target sdd_private_session_prod -t ratls-test .

./gsc build -c ../config.yaml --rm ratls-test ../private-session.manifest

./gsc sign-image -c ../config.yaml  ratls-test /home/azureuser/.config/gramine/enclave-key.pem

./gsc info-image gsc-ratls-test

docker run --device=/dev/sgx_enclave -v /var/run/aesmd/aesm.socket:/var/run/aesmd/aesm.socket -p 8000:8000 --rm gsc-ratls-test

docker run --device=/dev/sgx_enclave -v /var/run/aesmd/aesm.socket:/var/run/aesmd/aesm.socket -p 8000:8000 -v /home/azureuser/work/sdd-poc-server/private-sessions/tmp/:/app/tmp/ --rm gsc-ratls-test

docker run --device=/dev/sgx_enclave -v /var/run/aesmd/aesm.socket:/var/run/aesmd/aesm.socket --rm -it --entrypoint /bin/bash gsc-ratls-test

docker image rm gsc-ratls-test gsc-ratls-test-unsigned:latest ratls-test:latest

mr_enclave = "979127286e37c5078dfd7e0ea76e1de44eb1cf4d2ef796f7ff782b8b60042272"
mr_signer = "c3f66efa33385b1e61a24f8ff52f89c3aee05737bc79eba92aa0f9cac97f7626"