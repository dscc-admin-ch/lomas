#!/bin/bash

pip install isort==5.13.2
pip install black==24.4.2
pip install flake8==7.1.0
pip install mypy==1.10.0
pip install pylint==3.1.0

isort .
black .
flake8 .
mypy .

cd ./lomas_server
pylint .