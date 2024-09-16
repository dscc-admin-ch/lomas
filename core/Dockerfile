FROM python:3.12 AS lomas_core_base

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./lomas_core/ /code/lomas_core/
COPY ./setup.py /code/setup.py
COPY ./README.md /code/README.md

FROM lomas_core_base AS lomas_core_dev
RUN pip install -e /code/

FROM lomas_core_base AS lomas_core
RUN pip install -e /code/