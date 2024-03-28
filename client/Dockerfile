FROM python:3.11 as sdd_client_base

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM sdd_client_base AS sdd_client_dev
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

FROM sdd_client_base AS sdd_client
COPY ./dscc_sdd_client/ /code/dscc_sdd_client
COPY ./images/ /code/images/
COPY ./LICENSE /code/LICENSE
COPY ./Demo_Client_Notebook.ipynb /code/Demo_Client_Notebook.ipynb

CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]