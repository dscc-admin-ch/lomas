# To install packages including opendp_polars and opendp_logger 
FROM python:3.11-bullseye as sdd_private_session

# To install missing packages
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt 

WORKDIR /code
FROM sdd_private_session AS sdd_private_session_prod
COPY ./src/ /code/
COPY ./LICENSE /code/LICENSE
CMD ["python", "uvicorn_serve.py"]

FROM sdd_private_session AS sdd_private_session_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]