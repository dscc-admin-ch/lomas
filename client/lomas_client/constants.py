import os

CLIENT_SERVICE_NAME = os.getenv("CLIENT_SERVICE_NAME", "lomas-server-app")
SERVICE_ID = os.getenv("HOSTNAME", "default-host")

DUMMY_NB_ROWS = 100
DUMMY_SEED = 42


CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 10
DIFFPRIVLIB_READ_TIMEOUT = DEFAULT_READ_TIMEOUT * 10
SMARTNOISE_SYNTH_READ_TIMEOUT = DEFAULT_READ_TIMEOUT * 100

SNSYNTH_DEFAULT_SAMPLES_NB = 200
