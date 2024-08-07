"""
The content of this file is largely inspired from the
corresponding C implementation of the Gramine gramine-ratls
utility tool.

TODO: The license information needs to be sorted out
"""

import ctypes


def get_pem_bytes_from_der(
    header, footer, ctypes_der_ptr, ctypes_der_size
) -> bytes:
    """
    This function loads the mbetls library that comes with gramine
    installs (mbedtls_gramine.so) and calls the mbedtls_pem_write_buffer
    to transform certificate in "der" format to one in "pem" format.

    The result is returned as a python byte object and can be directly
    written to disk.

    This function is largely inspired from the "der_to_pem" function
    defined in the Gramine implementation of the gramine-ratls utility.

    Args:
        header (str): Python string for pem header
        footer (str): Python string for pem footer
        ctypes_der_ptr (ctypes.POINTER(ctypes.c_ubyte)):
                      ctypes pointer to der cert
        ctypes_der_size (ctypes.c_size_t):
                      ctypes.c_size_t size of the der cert
    """
    # Load correct library, function and define input/output types
    lib_mbedtls = ctypes.cdll.LoadLibrary("libmbedtls_gramine.so")

    func_mbedtls_pem_write_buffer = lib_mbedtls.mbedtls_pem_write_buffer
    func_mbedtls_pem_write_buffer.argtypes = [
        ctypes.c_char_p,  # header
        ctypes.c_char_p,  # footer
        ctypes.POINTER(ctypes.c_ubyte),  # der_ptr
        ctypes.c_size_t,  # der_size
        ctypes.POINTER(ctypes.c_char),  # pem
        ctypes.c_size_t,  # buf_size
        ctypes.POINTER(ctypes.c_size_t),  # bytes written
    ]
    func_mbedtls_pem_write_buffer.restype = ctypes.c_int

    # Create required args and convert python string to
    # \x00 terminated c-strings
    buf_size = ctypes.c_size_t()
    header = ctypes.c_char_p(header.encode("utf-8") + b"\x00")
    footer = ctypes.c_char_p(footer.encode("utf-8") + b"\x00")

    # First call to get buffer size
    ret = func_mbedtls_pem_write_buffer(
        header,
        footer,
        ctypes_der_ptr,
        ctypes_der_size,
        None,
        0,
        ctypes.byref(buf_size),
    )

    if ret == 0:
        # This should never happen since we feed a zero length buffer
        raise Exception(
            "Internal error while executing mbedtls_pem_write_buffer.",
            "Maybe check der size",
        )
    elif ret != -42:  # Should be MBEDTLS_ERR_BASE64_BUFFER_TOO_SMALL
        raise Exception(
            "Internal error while executing mbedtls_pem_write_bufer.",
            "Got {ret}.",
        )

    # Allocate memory and call again to write
    pem = (ctypes.c_char * buf_size.value)()
    # Tried using a reference for this but got an
    # ArgumentType error from ctypes
    pem_pointer = ctypes.cast(
        ctypes.pointer(pem), ctypes.POINTER(ctypes.c_char)
    )

    # Second call to fill pem buffer
    ret = func_mbedtls_pem_write_buffer(
        header,
        footer,
        ctypes_der_ptr,
        ctypes_der_size,
        pem_pointer,
        buf_size,
        ctypes.byref(buf_size),
    )

    if ret != 0:
        raise Exception(
            "Internal error while executing mbedtls_pem_write_bufer.",
            "Got {ret}.",
        )

    return bytes(pem)


def write_ra_tls_key_and_crt(
    key_file_path: str, cert_file_path: str, format: str = "pem"
) -> None:
    """
    This function loads the gramine libra_tls_attest.so
    binary library and calls the ra_tls_create_key_and_crt_der
    function to get the ra-tls key and certificate
    for the enclave it's running in.

    The key and certificate content are then written out
    either in "der" or "pem" format to the specified location.

    Args:
        key_file_path (str):  The file path for the created key
        cert_file_path (str): The file path for the created crt
        format (str): The format of the output files ("der" or "pem")
    """
    # Load library
    lib_ra_tls = ctypes.cdll.LoadLibrary("libra_tls_attest.so")

    # Get function and set arg and return types
    func_create_key_and_crt = lib_ra_tls.ra_tls_create_key_and_crt_der
    func_create_key_and_crt.argtypes = [
        ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    func_create_key_and_crt.restype = ctypes.c_int

    # Create argument values and call function
    key_ptr = ctypes.POINTER(ctypes.c_ubyte)()
    key_size = ctypes.c_size_t()
    crt_ptr = ctypes.POINTER(ctypes.c_ubyte)()
    crt_size = ctypes.c_size_t()

    ret = func_create_key_and_crt(
        ctypes.byref(key_ptr),
        ctypes.byref(key_size),
        ctypes.byref(crt_ptr),
        ctypes.byref(crt_size),
    )

    if ret < 0:
        raise Exception(
            (
                "Non-zero return value for ra_tls_create_key_and_crt_der",
                "function. Value was {ret}",
            )
        )

    if format == "pem":
        # Note: ried using ssl.DER_cert_to_PEM_cert() but did not work out
        key_bytes_dem = get_pem_bytes_from_der(
            "-----BEGIN EC PRIVATE KEY-----\n",
            "-----END EC PRIVATE KEY-----\n",
            key_ptr,
            key_size,
        )

        crt_bytes_dem = get_pem_bytes_from_der(
            "-----BEGIN TRUSTED CERTIFICATE-----\n",
            "-----END TRUSTED CERTIFICATE-----\n",
            crt_ptr,
            crt_size,
        )
    elif format == "der":
        # Need to cast key and crt to correct size
        # to get their contents as python bytes
        key_bytes_dem = ctypes.cast(
            key_ptr, ctypes.POINTER(ctypes.c_ubyte * key_size.value)
        ).contents
        crt_bytes_dem = ctypes.cast(
            crt_ptr, ctypes.POINTER(ctypes.c_ubyte * crt_size.value)
        ).contents
    else:
        raise Exception(
            f'Format should be either "der" or "pem", but was {format}.'
        )

    with open(key_file_path, "wb") as key_file:
        key_file.write(key_bytes_dem)

    with open(cert_file_path, "wb") as crt_file:
        crt_file.write(crt_bytes_dem)
