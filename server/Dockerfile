FROM dsccadminch/lomas_core AS lomas_server_base

WORKDIR /code

COPY ./requirements_server.txt /code/requirements_server.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements_server.txt 

FROM lomas_server_base AS lomas_server
COPY ./lomas_server/ /code/lomas_server/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_server_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "lomas_server.uvicorn_serve"]

FROM lomas_server_base AS lomas_admin_dashboard_base
COPY ./requirements_streamlit.txt /requirements_streamlit.txt
RUN pip install --no-cache-dir --upgrade -r /requirements_streamlit.txt

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard
COPY ./lomas_server/ /code/lomas_server/
COPY ./LICENSE /code/LICENSE
COPY ./data/ /data/
CMD ["streamlit", "run", "lomas_server/administration/dashboard/about.py"]

FROM lomas_admin_dashboard_base AS lomas_admin_dashboard_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["streamlit", "run", "lomas_server/administration/dashboard/about.py"]
