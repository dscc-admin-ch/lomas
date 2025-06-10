FROM python:3.12 AS lomas
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

# Copy pyproject files
COPY ./pyproject.toml /code/pyproject.toml
COPY ./core/pyproject.toml /code/core/pyproject.toml
COPY ./client/pyproject.toml /code/client/pyproject.toml
COPY ./server/pyproject.toml /code/server/pyproject.toml
COPY ./uv.lock /code/uv.lock

### CORE
# Base -> only deps
FROM lomas AS lomas_core_base
RUN uv sync --frozen --package lomas-core --no-cache --no-install-workspace
# Add executables to path, enables no need to uv run
ENV PATH="/code/.venv/bin:$PATH"

# Normal -> with source code
FROM lomas_core_base AS lomas_core
COPY ./core/README.md /code/core/README.md
COPY ./core/lomas_core/ /code/core/lomas_core/
RUN uv sync --package lomas-core


### CLIENT
FROM lomas_core_base AS lomas_client_base
RUN uv sync --package lomas-client --no-cache --no-install-workspace

# Dev -> deps and command
FROM lomas_client_base AS lomas_client_dev
WORKDIR /code/client
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="${PYTHONPATH}:/code/core:/code/client"
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

FROM lomas_client_base AS lomas_client
WORKDIR /code/client
COPY --from=lomas_core /code/ /code/
COPY ./client/lomas_client/ /code/client/lomas_client/
COPY ./client/README.md /code/client/README.md
COPY ./client/notebooks/images/ /code/client/notebooks/images/
COPY ./client/notebooks/Demo_Client_Notebook.ipynb /code/client/notebooks/Demo_Client_Notebook.ipynb
COPY ./client/LICENSE /code/client/LICENSE
COPY ./server/lomas_server/ /code/server/lomas_server/
RUN uv sync --package lomas-client --no-cache
ENV PYTHONPATH="${PYTHONPATH}:/code/core:/code/client:/code/server"
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

### SERVER
FROM lomas_core_base AS lomas_server_base
RUN uv sync --package lomas-server --no-cache --no-install-workspace

FROM lomas_server_base AS lomas_server_dev
WORKDIR /code/server
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="${PYTHONPATH}:/code/core:/code/server"
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_server
COPY --from=lomas_core /code/ /code/
COPY ./server/README.md /code/server/README.md
COPY ./server/lomas_server/ /code/server/lomas_server/
COPY ./server/LICENSE /code/server/LICENSE
COPY ./server/data/ /data/
RUN uv sync --package lomas-server --no-cache
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

### ADMIN
FROM lomas_server_base AS lomas_admin_base
RUN uv sync --package lomas-server --no-cache --no-install-workspace --extra all

FROM lomas_admin_base AS lomas_admin_dev
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="${PYTHONPATH}:/code/core:/code/server"
CMD ["streamlit", "run", "server/lomas_server/administration/dashboard/about.py"]

FROM lomas_admin_base AS lomas_admin
COPY --from=lomas_server /code/ /code/
COPY --from=lomas_server /data/ /data/
RUN uv sync --package lomas-server --no-cache --extra all
CMD ["streamlit", "run", "server/lomas_server/administration/dashboard/about.py"]
