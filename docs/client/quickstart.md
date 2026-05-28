# Quickstart

This is the quickstart guide for Lomas-client, providing initial setup and usage instructions.

## Client

## Prerequisites

We assume you have a lomas-server already running. If you want to quickly spin one, check [this documentation](../server/deployment/devenv.md) before going to the next step.

### Installation

To install lomas-client, follow these steps:

1. Open a terminal.
2. Run the following command: ```pip install lomas-client```
3. You're all set!

### First steps

To use FSO lomas client, you can do the following:

1. Import the library in your Python code.
2. Initialise the client with required url, name and dataset.
3. You can now use any function as long as you have access to the dataset!

```.python
# Step 1
from lomas_client import Client

# Step 2
# The following would usually be set in the environment by a system administrator
# and be tranparent to lomas users.
# Uncomment them if you are running against a Kubernetes deployment.
# They have already been set for you if you are running locally within a devenv or the Jupyter lab set up by Docker compose.

import os
# os.environ["LOMAS_CLIENT_APP_URL"] = "https://lomas.example.com:443"
# os.environ["LOMAS_CLIENT_OIDC_DISCOVERY_URL"] = "https://dex.example.com:443/.well-known/openid-configuration"
# os.environ["LOMAS_CLIENT_TELEMETRY__ENABLED"] = "false"
# os.environ["LOMAS_CLIENT_TELEMETRY__COLLECTOR_ENDPOINT"] = "http://otel.example.com:445"
# os.environ["LOMAS_CLIENT_TELEMETRY__COLLECTOR_INSECURE"] = "true"
# os.environ["LOMAS_CLIENT_TELEMETRY__SERVICE_ID"] = "my-app-client"
# os.environ["LOMAS_CLIENT_REALM"] = "lomas"

# We set these ones because they are specific to this notebook.

os.environ["LOMAS_CLIENT_USER_NAME"] = "dr.antartica@example.com"
os.environ["LOMAS_CLIENT_USER_PASSWORD"] = "dr.antartica"
os.environ["LOMAS_CLIENT_DATASET_NAME"] = "PENGUIN"

# Note that all client settings can also be passed as keyword arguments to the Client constructor.
# eg. client = Client(user_name = "Dr.Antartica") takes precedence over setting the "LOMAS_CLIENT_USER_NAME"
# environment variable.

# Step 3
res = client.available_dp_library.any_query(parameters)
```

with `any_query` being one of the function presented below and `parameters` being its associated parameters.

The currently supported methods in `available_dp_library` are documented in [this section](./opendp.md).