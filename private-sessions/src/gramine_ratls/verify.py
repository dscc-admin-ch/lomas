"""
Largely inspired from
https://github.com/gramineproject/gramine/commit/1a1869468aef7085d6c9d722adf9d1d0484e1b4c # noqa: E501
"""

import ctypes
import http.client
import os
import ssl
import urllib.parse


class AttestationError(Exception):
    pass


class Client:
    def __init__(
        self,
        url,
        mr_enclave,
        mr_signer,
        isv_prod_id,
        isv_svn,
        allow_debug_enclave_insecure,
        allow_outdated_tcb_insecure,
        allow_hw_config_needed,
        allow_sw_hardening_needed,
        protocol="dcap",
    ):
        # Parse url and enforce TLS
        self.url = urllib.parse.urlsplit(url)
        if self.url.scheme != "https":
            raise ValueError(f"Needs https:// URI, found {self.url.scheme}")

        # Require at least enclave or signer measurement
        if (mr_enclave, mr_signer) == (None, None):
            raise TypeError("Need at least one of: mrenclave, mrsigner")

        self.mr_enclave = mr_enclave
        self.mr_signer = mr_signer
        self.isv_prod_id = isv_prod_id
        self.isv_svn = isv_svn

        self.allow_debug_enclave_insecure = allow_debug_enclave_insecure
        self.allow_outdated_tcb_insecure = allow_outdated_tcb_insecure
        self.allow_hw_config_needed = allow_hw_config_needed
        self.allow_sw_hardening_needed = allow_sw_hardening_needed

        # Only supports dcap for now
        if protocol != "dcap":
            raise ValueError("Only dcap verification supported")

        self.protocol = protocol

        # Load gramine ra_tls verify callback function once for all
        lib_ra_tls = ctypes.cdll.LoadLibrary("libra_tls_verify_dcap.so")
        """
        TODO
        The following call triggers a warning because it will be deprecated.
        Checked for using the ..._extended function but it uses enums.
        Need to sort out how to do enum types.
        """
        self._func_ra_tls_verify_callback = (
            lib_ra_tls.ra_tls_verify_callback_der
        )
        self._func_ra_tls_verify_callback.argtypes = (
            ctypes.c_char_p,
            ctypes.c_size_t,
        )
        self._func_ra_tls_verify_callback.restype = ctypes.c_int

    def _ra_tls_setenv(self, var, value, default=None):
        """
        Utils function for properly setting ra-tls environment variables.
        """
        if value in (None, False):
            if default is None:
                try:
                    del os.environ[var]
                except KeyError:
                    pass
            else:
                os.environ[var] = default
        elif value is True:
            os.environ[var] = "1"
        else:
            os.environ[var] = value

    def _verify_ra_tls_cb(self, cert):
        # Set environment variables for gramine verification function to use
        self._ra_tls_setenv("RA_TLS_MRENCLAVE", self.mr_enclave, "any")
        self._ra_tls_setenv("RA_TLS_MRSIGNER", self.mr_signer, "any")
        self._ra_tls_setenv("RA_TLS_ISV_PROD_ID", self.isv_prod_id, "any")
        self._ra_tls_setenv("RA_TLS_ISV_SVN", self.isv_svn, "any")

        self._ra_tls_setenv(
            "RA_TLS_ALLOW_DEBUG_ENCLAVE_INSECURE",
            self.allow_debug_enclave_insecure,
        )
        self._ra_tls_setenv(
            "RA_TLS_ALLOW_OUTDATED_TCB_INSECURE",
            self.allow_outdated_tcb_insecure,
        )
        self._ra_tls_setenv(
            "RA_TLS_ALLOW_HW_CONFIG_NEEDED", self.allow_hw_config_needed
        )
        self._ra_tls_setenv(
            "RA_TLS_ALLOW_SW_HARDENING_NEEDED", self.allow_sw_hardening_needed
        )

        # Execute gramine callback function and check result
        ret = self._func_ra_tls_verify_callback(cert, len(cert))
        if ret < 0:
            raise AttestationError(ret)

    def _request(self, method, endpoint, headers={}, data=None):
        # Create TLS connection
        context = (
            ssl._create_unverified_context()
        )  # pylint: disable=protected-access
        conn = http.client.HTTPSConnection(self.url.netloc, context=context)
        conn.connect()

        # Verify enclave attestation with proper callback function
        try:
            # NEVER SEND ANYTHING TO THE SERVER BEFORE THIS LINE
            self._verify_ra_tls_cb(conn.sock.getpeercert(binary_form=True))
        except AttestationError:
            conn.close()
            raise

        # Setup and send request
        path = self.url.path
        if self.url.query:
            path += self.url.query
        path = f"{path}/{endpoint}"

        headers = {
            "host": self.url.hostname,
            **headers,
        }

        conn.request(method, path, body=data)
        return conn.getresponse()

    def get(self, endpoint, headers={}):
        return self._request("GET", endpoint, headers)

    def post(self, endpoint, headers={}, data=None):
        return self._request("POST", endpoint, headers, data)
