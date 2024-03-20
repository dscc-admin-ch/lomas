FROM python:3.11 as sdd_client

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM sdd_client AS sdd_client_dev
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

FROM sdd_client AS sdd_client_prod
COPY ./fso_sdd_demo/ /code/fso_sdd_demo
COPY ./demo_notebooks/images/ /code/images/
COPY ./LICENCE /code/LICENCE
COPY ./demo_notebooks/Demo_Client_Notebook.ipynb /code/Demo_Client_Notebook.ipynb
CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]