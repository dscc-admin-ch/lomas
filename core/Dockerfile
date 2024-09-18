FROM python:3.12 AS lomas_core

WORKDIR /code

COPY ./requirements_core.txt /code/requirements_core.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements_core.txt

COPY ./lomas_core/ /code/lomas_core/
COPY ./setup.py /code/setup.py
COPY ./README.md /code/README.md

RUN pip install -e /code/