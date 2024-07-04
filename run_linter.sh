#!/bin/bash

install_dependencies() {
    pip install isort==5.13.2
    pip install black==24.4.2
    pip install flake8==7.1.0
    pip install mypy==1.10.0
    pip install pylint==3.1.0
}

# Parse command line arguments for --install-deps flag
INSTALL_DEPS=false
for arg in "$@"; do
    if [ "$arg" == "--install-deps" ]; then
        INSTALL_DEPS=true
        break
    fi
done

# Install dependencies if flag is set
if [ "$INSTALL_DEPS" == true ]; then
    install_dependencies
fi


cd server/lomas_server
isort .
black .
flake8 .
pylint .

cd ..
mypy .

cd ../client/lomas_client
isort .
black .
flake8 .
pylint .

cd ..
mypy .
