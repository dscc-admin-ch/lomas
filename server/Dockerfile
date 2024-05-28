# To install packages including opendp_polars and opendp_logger 
FROM python:3.11 as lomas_server_base

# To install missing packages
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt 

WORKDIR /code

FROM lomas_server_base AS lomas_server
# Switch to non-root user
USER 1000
COPY ./lomas_server/ /code/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["python", "uvicorn_serve.py"]

FROM lomas_server_base AS lomas_server_dev
# Switch to non-root user
USER 1000
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]

FROM lomas_server_base AS lomas_streamlit_base
COPY ./requirements_streamlit.txt /requirements_streamlit.txt
RUN pip install --no-cache-dir --upgrade -r /requirements_streamlit.txt

FROM lomas_streamlit_base AS lomas_streamlit
# Switch to non-root user
USER 1000
COPY ./lomas_server/ /code/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["streamlit", "run", "administration/dashboard/about.py"]

FROM lomas_streamlit_base AS lomas_streamlit_dev
# Switch to non-root user
USER 1000
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["streamlit", "run", "administration/dashboard/about.py"]
