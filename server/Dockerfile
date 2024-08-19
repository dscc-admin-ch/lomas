# To install packages including opendp_polars and opendp_logger 
FROM python:3.11 as lomas_server_base

# To install missing packages
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r /requirements.txt
# Need to do that manually because of version conflicts.
RUN pip install opendp==0.10.0a20240724001

WORKDIR /code

FROM lomas_server_base AS lomas_server
COPY ./lomas_server/ /code/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["python", "uvicorn_serve.py"]

FROM lomas_server_base AS lomas_server_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]

FROM lomas_server_base AS lomas_admin_dashboard_base
COPY ./requirements_streamlit.txt /requirements_streamlit.txt
RUN pip install --no-cache-dir --upgrade -r /requirements_streamlit.txt

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard
COPY ./lomas_server/ /code/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["streamlit", "run", "administration/dashboard/about.py"]

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["streamlit", "run", "administration/dashboard/about.py"]
