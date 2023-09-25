# Rust Stage 

FROM rust:latest AS rust_opendp_compile

# Clone branch of git repository
RUN git clone -b 911-make-private-select https://github.com/damienaymon/opendp-fso.git

# Build the Rust library
RUN mv opendp-fso opendp
WORKDIR opendp/rust
RUN cargo build --features untrusted,bindings-python

# Python stage
FROM python:3.8 AS sdd_server
COPY --from=rust_opendp_compile opendp/ opendp_polars/

# Install python opendp under the name opendp_polars
WORKDIR opendp_polars/python
RUN sed -i 's/setup()/setup(name="opendp_polars")/' setup.py 
RUN sed -i 's/name = opendp/name = opendp_polars/' setup.cfg
RUN mv src/opendp src/opendp_polars
RUN sed -i 's/opendp\./opendp_polars\./' src/opendp_polars/*.py
RUN pip install flake8 pytest wheel
RUN pip install -e .

# Install opendp_logger using previously installed opendp_polars
RUN git clone https://github.com/opendp/opendp-logger
WORKDIR opendp-logger
# Remove opendp dependency from PyPI; use local opendp_polars installation 
# via find_packages() from setuptools
RUN sed -i '/"opendp >= 0.8.0"/d' setup.py 
RUN sed -i 's/opendp\./opendp_polars\./' opendp_logger/*.py
RUN pip install -e .

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#RUN git clone https://github.com/IBM/differential-privacy-library
#RUN cd differential-privacy-library && pip install .

#RUN rm -rf differential-privacy-library

# We do not copy the code here, but in the test and prod stages only.
# For developping, we mount a volume with the -v option at runtime.
#COPY ./src/ /code/

FROM sdd_server AS sdd_server_test
# run tests with pytest
COPY ./src/ /code/
COPY ./tests/ /code/tests/
COPY .configs/example_config.yaml /usr/sdd_poc_server/runtime.yaml
CMD ["python", "-m", "pytest", "tests/"]

FROM sdd_server AS sdd_server_prod
COPY ./src/ /code/
# run as local server
# Disable this for now, as we do not run a mongodb instance.
COPY ./configs/example_config.yaml /usr/sdd_poc_server/runtime.yaml
CMD ["python", "uvicorn_serve.py"]

FROM sdd_server AS sdd_server_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]
# Empty, used for development.