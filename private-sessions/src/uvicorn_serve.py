import uvicorn

from utils.loggr import LOG
from gramine_ratls.attest import write_ra_tls_key_and_crt


if __name__ == "__main__":

    key_file_path = "/app/tmp/key.pem"
    crt_file_path = "/app/tmp/crt.pem"

    LOG.info("Generating ra-tls certificates")
    write_ra_tls_key_and_crt(key_file_path, crt_file_path, format="pem")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        # Cannot use multiprocessing in gramine
        # because the tmpfs file system we write
        # the certificates to with gramine-ratls
        # is not shared between enclaves.
        workers=1,
        # Cannot use this because it uses multiprocessing.
        reload=False,
        ssl_keyfile=key_file_path,
        ssl_certfile=crt_file_path,
    )
