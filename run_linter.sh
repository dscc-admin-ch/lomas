#!/bin/bash

# Parse command line arguments
INSTALL_DEPS=false
RUN_CLIENT=false
RUN_SERVER=false
RUN_CORE=false

for arg in "$@"; do
    case $arg in
        --install-deps)
            INSTALL_DEPS=true
            ;;
        --client)
            RUN_CLIENT=true
            ;;
        --server)
            RUN_SERVER=true
            ;;
        --core)
            RUN_CORE=true
            ;;
    esac
done


# Install dependencies if flag is set
if [ "$INSTALL_DEPS" == true ]; then
    pip install -r requirements-dev.txt
fi

# If none selected, then run all
if [ "$RUN_CLIENT" == false ] && [ "$RUN_SERVER" == false ] && [ "$RUN_CORE" == false ]; then
    RUN_CLIENT=true
    RUN_SERVER=true
    RUN_CORE=true
fi

if [ "$RUN_SERVER" == true ]; then
    echo "Running linting and type checking for server..."
    isort server/lomas_server
    black server/lomas_server
    flake8 --toml-config=./pyproject.toml server/lomas_server
    mypy server/lomas_server
    pylint server/lomas_server
    pydocstringformatter -w server/lomas_server
fi

if [ "$RUN_CLIENT" == true ]; then
    echo "Running linting and type checking for client..."
    isort client/lomas_client
    black client/lomas_client
    flake8 --toml-config=./pyproject.toml client/lomas_client
    mypy client/lomas_client
    pylint client/lomas_client
    pydocstringformatter -w client/lomas_client
fi

if [ "$RUN_CORE" == true ]; then
    echo "Running linting and type checking for core..."
    isort core/lomas_core
    black core/lomas_core
    flake8 --toml-config=./pyproject.toml core/lomas_core
    mypy core/lomas_core
    pylint core/lomas_core
    pydocstringformatter -w core/lomas_core
fi
