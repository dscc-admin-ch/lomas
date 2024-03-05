# To install packages including opendp_polars and opendp_logger 
FROM dtlam/sdd_server_opendp_polars:1.2 as sdd_server

# To install missing packages
RUN pip install smartnoise-sql==1.0.0
RUN pip install boto3

WORKDIR /
RUN git clone --branch polars https://github.com/opendp/opendp-logger
WORKDIR opendp-logger
RUN sed -i '/"opendp >= 0.8.0"/d' setup.py
RUN sed -i 's/opendp\./opendp_polars\./' opendp_logger/*.py
RUN sed -i 's/get_distribution("opendp")/get_distribution("opendp_polars")/' opendp_logger/*.py
RUN pip install -e .

WORKDIR /code
FROM sdd_server AS sdd_server_prod
COPY ./src/ /code/
COPY ./data/ /data/
CMD ["python", "uvicorn_serve.py"]

FROM sdd_server AS sdd_server_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]