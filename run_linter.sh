#!/bin/bash

install_dependencies() {
    pip install isort==5.13.2
    pip install black==24.4.2
    pip install flake8-pyproject==1.2.3
    pip install mypy==1.10.0
    pip install pylint==3.1.0
}

# Parse command line arguments for --install-deps flag
INSTALL_DEPS=false
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
    install_dependencies
fi

# If none selected, then run all
if [ "$RUN_CLIENT" == false ] && [ "$RUN_SERVER" == false ] && [ "$RUN_CORE" == false ]; then
    RUN_CLIENT=true
    RUN_SERVER=true
    RUN_CORE=true
fi

if [ "$RUN_SERVER" == true ]; then
    echo "Running linting and type checking for server..."
    cd server/lomas_server
    isort .
    black .
    flake8 --toml-config=../pyproject.toml .
    pylint .

    cd ..
    mypy .

    cd ..
fi

if [ "$RUN_CLIENT" == true ]; then
    echo "Running linting and type checking for client..."
    cd client/lomas_client
    isort .
    black .
    flake8 --toml-config=../pyproject.toml .
    pylint .

    cd ..
    mypy .

    cd ..
fi

if [ "$RUN_CORE" == true ]; then
    echo "Running linting and type checking for core..."
    cd core/lomas_core
    isort .
    black .
    flake8 --toml-config=../pyproject.toml .
    pylint .

    cd ..
    mypy .

    cd ..
fi