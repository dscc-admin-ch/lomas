FROM python:3.12 AS lomas_core

WORKDIR /code

COPY ./core/requirements_core.txt /code/requirements_core.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements_core.txt

COPY ./core/lomas_core/ /code/lomas_core/

ENV PYTHONPATH="${PYTHONPATH}:/code/"

### CLIENT
FROM lomas_core AS lomas_client_base
WORKDIR /code

COPY ./client/requirements_client.txt /code/requirements_client.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements_client.txt

FROM lomas_client_base AS lomas_client_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

FROM lomas_client_base AS lomas_client
COPY ./client/lomas_client/ /code/lomas_client/
COPY ./client/README.md /code/README.md
COPY ./client/notebooks/images/ /code/notebooks/images/
COPY ./client/notebooks/Demo_Client_Notebook.ipynb /code/notebooks/Demo_Client_Notebook.ipynb
COPY ./client/LICENSE /code/LICENSE
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

### SERVER
FROM lomas_core AS lomas_server_base

COPY ./server/requirements_server.txt /code/requirements_server.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements_server.txt 

FROM lomas_server_base AS lomas_server_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_server
COPY ./server/lomas_server/ /code/lomas_server/
COPY ./server/LICENSE /code/LICENSE
COPY ./server/data/ /data/
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_admin_dashboard_base
COPY ./server/requirements_streamlit.txt /requirements_streamlit.txt
RUN pip install --no-cache-dir --upgrade -r /requirements_streamlit.txt

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["streamlit", "run", "lomas_server/administration/dashboard/about.py"]

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard
COPY ./server/lomas_server/ /code/lomas_server/
COPY ./server/LICENSE /code/LICENSE
COPY ./server/data/ /data/
CMD ["streamlit", "run", "lomas_server/administration/dashboard/about.py"]