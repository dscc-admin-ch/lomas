FROM python:3.12 AS lomas_core

WORKDIR /code

COPY ./core/pyproject.toml /code/pyproject.toml
RUN uv pip sync --no-cache

COPY ./core/lomas_core/ /code/lomas_core/

ENV PYTHONPATH="${PYTHONPATH}:/code/"

### CLIENT
FROM lomas_core AS lomas_client_base
WORKDIR /code

COPY ./client/pyproject.toml /code/pyproject.toml
RUN uv pip sync --no-cache

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

COPY ./server/pyproject.toml /code/pyproject.toml
RUN uv pip sync --no-cache

FROM lomas_server_base AS lomas_server_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_server
COPY ./server/lomas_server/ /code/lomas_server/
COPY ./server/LICENSE /code/LICENSE
COPY ./server/data/ /data/
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_admin_dashboard_base
RUN uv pip sync --no-cache --extra all

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["streamlit", "run", "lomas_server/administration/dashboard/about.py"]

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard
COPY ./server/lomas_server/ /code/lomas_server/
COPY ./server/LICENSE /code/LICENSE
COPY ./server/data/ /data/
CMD ["streamlit", "run", "lomas_server/administration/dashboard/about.py"]
