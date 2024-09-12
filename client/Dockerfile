FROM python:3.11 AS lomas_client_base

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
# Need to do that manually because of version conflicts.
RUN pip install opendp==0.11.1

COPY ./lomas_client/ /code/lomas_client/
COPY ./setup.cfg /code/setup.cfg
COPY ./setup.py /code/setup.py
COPY ./README.md /code/README.md

FROM lomas_client_base AS lomas_client_dev
RUN pip install -e /code/

CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]

FROM lomas_client_base AS lomas_client
COPY ./notebooks/images/ /code/notebooks/images/
COPY ./LICENSE /code/LICENSE
COPY ./notebooks/Demo_Client_Notebook.ipynb /code/notebooks/Demo_Client_Notebook.ipynb
COPY ./notebooks/Demo_Client_Notebook_DiffPrivLib.ipynb /code/notebooks/Demo_Client_Notebook_DiffPrivLib.ipynb

RUN pip install -e /code/

CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]