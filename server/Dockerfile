# To install packages including opendp_polars and opendp_logger 
FROM python:3.11 as sdd_server

# To install missing packages
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt 

WORKDIR /code
FROM sdd_server AS sdd_server_prod
COPY ./src/ /code/
COPY LICENCE /code/LICENCE
COPY ./data/ /data/
CMD ["python", "uvicorn_serve.py"]

FROM sdd_server AS sdd_server_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]