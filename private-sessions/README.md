# Private Sessions

This part of the repo gives a baseline for building a docker image for running a fastapi server inside an Intel SGX enclave
with Gramine as well as a Python client for it. The server attests itself by providing the relevant ra-tls certificates and the python client is able verify the attestation quote provided by the server.

This README also includes some information about the Gramine and Intel SGX setup (especially on Azure SGX enabled VMs).

The high-level process goes as follows:
- Build a standard docker image comprising the server. Before starting the fastapi app, the python server must create the ra-tls certificate and corresponding key using Gramine ra-tls binary libraries and write them to disk. These will be used by uvicorn as server certificate and provide the attestation to the client.
- "Graminize" the docker image with the GSC tool to run the fastapi server inside an SGX enclave.
- Run the client as a local python program, no SGX involved. The client verifies the attestation quote using Gramine ra-tls binary libraries.

## Setup and General Information

### Gramine and Intel SGX tools

We use Gramine to run the server inside an SGX enclave.

Let us (very briefly and on a very high level) explain how that works. Initially, SGX enclave were meant to be developped using the SGX development kit. An application would be "SGX aware" and be split into a "trusted" part, running inside SGX, and an "untrusted" part, running outside SGX. An application starts with untrusted code, and calls to EENTER and EEXIT instructions are required to enter/exit the enclave. The instruction set available to enclave code is very limited (e.g. no priviledged instructions, which means no system calls in the Linux world). The development of SGX aware application is usually done in compiled languages such as C++ and leverage the Intel provided SGX Software Development Kit.

Gramine started as a research project, with the goal of running entire standard applications inside SGX enclaves. It comes in the form of a Library OS (LibOS) that can be seen as the operating system that runs the target application. The LibOS intercepts all application requests that are made to the host OS (that would result in errors within SGX anyway), and either implements them itself or transfers them to the host OS and sanitizes the resutls. Gramine implements a Platform Adaptation Layer (PAL) for interfacing between the LibOS and the host OS. For more information on Intel SGX and Gramine, it is highly recommended to read the Gramine documentation in details. A very good starting point is [the Gramine Introduction to SGX](https://gramine.readthedocs.io/en/stable/sgx-intro.html) and the [Gramine features page](https://gramine.readthedocs.io/en/stable/sgx-intro.html).

Additionnally to protecting running code from higher priviledged processes, SGX also allows to verify the integrity of an application's trusted part, even remotely. Again, on a very very high level, enclave attestation works as follows: an enclave produces a quote (comprising code measurements, enclave author, hardware measurements, etc.) that is transfered to the remote verifier. The remote verifier then verifies the quote with the help of Intel (or the cloud provider's) quote verification services. Gramine also provides some higher level functionality to complete the enclave attestation/verification process. We will use ra-tls and focus on this option only here. The idea behind ra-tls is to include the attestation quote inside the standard TLS certificate. When the remote verifier connects to the enclave, it extracts the quote from the TLS certificate and verifies it before finishing the connection setup. For more information about this, it is highly recommended to read the [Gramine Attestation and Secret Provisioning](https://gramine.readthedocs.io/en/stable/attestation.html) page.

Let's continue our journey by installing Gramine:

- Install Gramine by following the instructions [here](https://gramine.readthedocs.io/en/latest/installation.html#ubuntu-22-04-lts-or-20-04-lts).

A few more steps and Intel SGX tools are required, see [here](https://gramine.readthedocs.io/en/latest/sgx-setup.html) for more content on this. The code in this repo does not directly interact with most of these components (only indirectly through Gramine, but a bit of context is good for general understanding):
- Create an SGX signing key with the command `gramine-sgx-gen-private-key`. This will write a pem key to `$HOME/.config/gramine/enclave-key` by default. Such a key is needed to sign enclaves at creation. Resulting measurements from this operation are used to verify enclave attestations once the enclave is deployed.
- Intel PSW (Platform SoftWare): (Note: this is already done on Azure SGX VMs). This provides several SGX functionalities from loading and initializing SGX enclaves to management of so-called "architectural" enclaves. It runs as a Linux service (aesm_service for Application Enclave Services Manager). For information, the interface to this service is through a socket located at /var/run/aesmd/aesm.socket (this will be usefull later, because we need to provide this socket to the server container). TODO: check if we had to install this + link to instructions
- Intel DCAP library: This binary library provides functionality for dcap quote generation and verification. TODO check if we had to install this + instructions
- Intel QPL library: This binary library provides functionality for the communication with DCAP verification services. TODO add qpl config + difference with azure_dcap library.

At this stage, it is highly recommended to check the setup by running the python `sgx-quote.py` example from the Gramine repository (see [here](https://github.com/gramineproject/gramine/tree/master/CI-Examples/python)). This will also help understand more about how an application is "graminized", The Gramine `is-sgx-available` can also be of good use.

### Gramine Shielded Containers

This tool is used to "graminize" a standard docker image so that its content can be executed within an SGX enclave.

If the reader has already played with the Gramine CI-Examples linked above, it should have some understanding of how to configure the process of "graminizing" an application with the manifest file and how to run it with Gramine-SGX. GSC automates this entire process for existing Docker images by creating a manifest file with the correct configuration (entrypoint, sgx trusted files, etc.) and a new image containing the required application files, a Gramine install as well as the signed enclave.

The GSC tool comes as a python script. It is installed by cloning [this](https://github.com/gramineproject/gsc) Git repository. Documentation for the tool as well as installation instructions can be found [here](https://gramine.readthedocs.io/projects/gsc/en/latest/).


## Python package for gramine ra-tls related functionality

Note: the package is currently located in ./src/gramine_ratls but we could consider publishing it as an independent package for
others to use.

As stated above, the server uses ra-tls to attest its code and runing environment. Before starting the fastapi app, the python server must create the ra-tls certificate and corresponding key using Gramine ra-tls binary libraries and write them to disk. These will be used by uvicorn as server certificate and provide the attestation to the client.

Gramine provides binary libraries for generating ra-tls certificates and verifying them. These are meant to be linked with applications built in compiled languages such as C. The Gramine repository contains such an example application with the [ra-tls-mbedtls example](https://github.com/gramineproject/gramine/tree/master/CI-Examples/ra-tls-mbedtls). Because we are using a fastapi application written in Python, as well as Python clients, we have to call the Gramine ra-tls functions directly from Python. Such an example is not yet provided in the Gramine repository.

Thus, this package offers functions for generating ra-tls certificates and verifying them in Python. It is built on top of and requires the Gramine ra-tls binary libraries that come with Gramine. Some of the code is heavily inspired from the C implementation of the Gramine gramine-ratls utility as well as the python code in [this](https://github.com/gramineproject/gramine/compare/woju/gramine-ratls-client) PR from the official Gramine repo.


Note on the gramine-ratls utility: As is demonstrated in the [ra-tls-nginx example](https://github.com/gramineproject/gramine/tree/master/CI-Examples/ra-tls-nginx), Gramine provides the gramien-ratls utility to generate ra-tls certificates for SGX "unaware applications". The gramine-ratls tool is used as entrypoint for the LibOS. It generates the ra-tls x.509 key and certificate (in pem or der format) before starting the main application itself. Using this tool requires changes to the Gramine manifest, namely libos.entrypoint and loader.argv, of which the latter is not supported in GSC. Indeed, GSC automatically generates an arguments file from the source Docker image's entrypoint/cmd and uses loader.argv_src_file, which is mutually exclusive with loader.argv. One could patch GSC to take this into account: loader.argv_src_file should be removed if loader.argv is manually specified by the user. TBD.

## Putting things together

To illustrate the usage of the python gramine-ratls library, we provide and example server and client implementation.

### Server

The server is located in `src/uvicorn_serve.py`: it calls into the gramine-ratls package for generating the ra-tls certificates and then starts the fastapi app in `src/app.py` with the required SSL/TLS configurations.

Note that the uvicorn server MUST run as a single process, hence why the number of workers is set to 1 and the reload option disabled. Gramine implements multiprocessing by starting separate enclaves for each process and having them communicate through secure channels. While Gramine enables mounting memory backed temporary file systems (tmpfs) within a single enclave, these are not persisted across multiple enclaves. Saving the ra-tls certificates in one process, but not being able to recover them in the second one breaks our application's ability to attest itself. Another option for writing files to disk is using the sgx.allowed files option in Gramine. This however uses the host OS's file system and is thus not safe.

To build the base docker image, use

```
docker build --target sdd_private_session_prod -t ratls-test .
```

The GSC configuration, the server's manifest file and the Python requirements file for GSC are all located in `gsc-configs` and it is assumed that GSC is manually cloned under `gsc-configs/gsc`. Finally, it is also expected that an SGX signing key was generated with the `gramine-sgx-gen-private-key` and saved to `/home/azureuser/.config/gramine/enclave-key.pem` (default behaviour).

To generate the graminized and signed Docker image for the server, run

```
cd gsc-configs/gsc/

./gsc build -c ../config.yaml --rm ratls-test ../private-session.manifest

./gsc sign-image -c ../config.yaml  ratls-test /home/azureuser/.config/gramine/enclave-key.pem

cd ../../
```

## Client

The client is implemented in `src/client.py`. It contains an implementation of a dummy python class for making requests to the server. The dummy client internally wraps the `Client` class provided by the gramine_ratls package (see `src/gramine_ratls/verify.py`) The gramine_ratls python client loads the required verification callback function from the Gramine ratls binary library and performs the verification at every connection/request. Its `get` and `post` functions return a python `http.HTTPResponse` object.

__Important__: Before using the client, update the main function of the `src/client.py` file with the correct `mr_signer` and `mr_enclave` of the graminized image with `./gsc info-image gsc-ratls-test`.


## Testing

Start the server with 

```
docker run --device=/dev/sgx_enclave -v /var/run/aesmd/aesm.socket:/var/run/aesmd/aesm.socket -p 8000:8000 --rm gsc-ratls-test
```

A few things happen here:
- The SGX device is "forwarded" to the container
- The aesm socket is mounted into the container for Gramine to be able to interact with the aesm service.
- Finally, the server port is exposed.

The client is finally tested by running
```
python client.py
```

## build.sh

The `build.sh` script automates the removal of old images and the rebuilding, graminizing and signing of the server image.







