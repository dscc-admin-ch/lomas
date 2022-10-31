# the dockerfile is for localhost testing and pytest
FROM python:3.8 AS pets_comp

WORKDIR /code
 
COPY ./requirements.txt /code/requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# # Install MBI for MST SD model
RUN pip install git+https://github.com/ryan112358/private-pgm.git

# # Install Smartnoise Synth from source to get the latest (incl MST)
RUN git clone https://github.com/opendp/smartnoise-sdk.git
RUN cd smartnoise-sdk/synth && python -m pip install .

RUN rm -rf smartnoise-sdk

RUN git clone https://github.com/IBM/differential-privacy-library
RUN cd differential-privacy-library && pip install .

RUN rm -rf differential-privacy-library

COPY ./src/ /code/

FROM pets_comp AS pets_comp_test
# run tests with pytest
COPY ./tests/ /code/tests/
CMD ["python", "-m", "pytest", "tests/"]

FROM pets_comp
# run as local server
COPY ./configs/example_config.yaml /usr/runtime.yaml
CMD ["python", "uvicorn_serve.py"]