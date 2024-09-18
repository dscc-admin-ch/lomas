FROM dsccadminch/lomas_core AS lomas_client_base

WORKDIR /code

COPY ./requirements_client.txt /code/requirements_client.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements_client.txt

FROM lomas_client_base AS lomas_client_dev
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

FROM lomas_client_base AS lomas_client
COPY ./lomas_client/ /code/lomas_client/
COPY ./README.md /code/README.md
COPY ./notebooks/images/ /code/notebooks/images/
COPY ./notebooks/Demo_Client_Notebook.ipynb /code/notebooks/Demo_Client_Notebook.ipynb
COPY ./LICENSE /code/LICENSE
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]