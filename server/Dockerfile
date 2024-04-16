# To install packages including opendp_polars and opendp_logger 
FROM python:3.11 as lomas_server_base

# To install missing packages
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt 

WORKDIR /code
FROM lomas_server_base AS lomas_server
COPY ./src/ /code/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["python", "uvicorn_serve.py"]

FROM lomas_server_base AS lomas_server_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]