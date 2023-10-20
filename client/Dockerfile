FROM dtlam/sdd_server_opendp_polars:1.2

WORKDIR /
RUN git clone --branch polars https://github.com/opendp/opendp-logger
WORKDIR opendp-logger
RUN sed -i '/"opendp >= 0.8.0"/d' setup.py
RUN sed -i 's/opendp\./opendp_polars\./' opendp_logger/*.py
RUN sed -i 's/get_distribution("opendp")/get_distribution("opendp_polars")/' opendp_logger/*.py
RUN pip install -e .

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN pip install jupyter
RUN pip install seaborn

CMD ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root", "--NotebookApp.token=''","--NotebookApp.password=''"]
