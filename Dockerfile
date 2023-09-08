# Rust Stage 

FROM rust:latest AS rust-stage

WORKDIR /code

# Clone branch of git repository
RUN git clone -b 911-make-private-select https://github.com/opendp/opendp.git

# Build the Rust library
WORKDIR /code/rust_opendp
RUN cargo build --release


# Python stage
FROM python:3.8 AS sdd_server

WORKDIR /code
 
COPY ./requirements.txt /code/requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN git clone https://github.com/IBM/differential-privacy-library
RUN cd differential-privacy-library && pip install .

RUN rm -rf differential-privacy-library

# We do not copy the code here, but in the test and prod stages only.
# For developping, we mount a volume with the -v option at runtime.
#COPY ./src/ /code/

FROM sdd_server AS sdd_server_test
# run tests with pytest
COPY ./src/ /code/
COPY ./tests/ /code/tests/
# Copy the compiled Rust library from the Rust stage
COPY --from=rust-stage /code/rust_opendp/target/release/* /code/
COPY .configs/example_config.yaml /usr/sdd_poc_server/runtime.yaml
CMD ["python", "-m", "pytest", "tests/"]

FROM sdd_server AS sdd_server_prod
COPY ./src/ /code/
# Copy the compiled Rust library from the Rust stage
COPY --from=rust-stage /code/rust_opendp/target/release/* /code/
# run as local server
# Disable this for now, as we do not run a mongodb instance.
COPY ./configs/example_config.yaml /usr/sdd_poc_server/runtime.yaml
CMD ["python", "uvicorn_serve.py"]

FROM sdd_server AS sdd_server_dev
ENV PYTHONDONTWRITEBYTECODE 1
CMD ["python", "uvicorn_serve.py"]
# Empty, used for development.