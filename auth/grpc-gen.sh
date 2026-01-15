DEX_VERSION=v2.42.0
wget https://raw.githubusercontent.com/dexidp/dex/${DEX_VERSION}/api/v2/api.proto

python -m grpc_tools.protoc -I. --pyi_out=./client --python_out=./client --grpc_python_out=./client ./api.proto
