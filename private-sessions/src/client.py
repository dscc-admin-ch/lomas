import json

from gramine_ratls.verify import Client


class CustomClient:

    def __init__(self, url, mr_enclave, mr_signer):
        self.client = Client(
            url,
            mr_enclave,
            mr_signer,
            0,  # These are dangerous, would have to be properly chosen and set
            0,
            True,
            True,
            True,
            True,
        )

    def get_some_greetings(
        self,
    ) -> None:
        # The gramine_ratls package returns an HTTPResponse object
        res = self.client.get("")

        # We only print the result here, but could do more
        if res.status == 200:
            print(res.read())
        else:
            print(res.status)

    def get_your_own_headers(
        self,
    ) -> None:
        headers = {"Content-type": "application/json", "Accept": "*/*"}
        headers["user-name"] = "test_user"

        endpoint = "get_headers"

        res = self.client.get(endpoint, headers)

        if res.status == 200:
            print(res.read())
        else:
            print(res.status)

    def log_some_string(
        self,
    ) -> None:
        endpoint = "log_body"
        body = json.dumps({"message": "Hi enclave!"}).encode("utf-8")

        res = self.client.post(endpoint, data=body)

        if res.status == 200:
            print(res.read())
        else:
            print(res.status)


if __name__ == "__main__":
    mr_enclave = (
        "8e7165ec1e2b9fec3bef2e0ddceefb54f2694b81aef0f11fe1f5f42ea9b1491f"
    )
    mr_signer = (
        "c3f66efa33385b1e61a24f8ff52f89c3aee05737bc79eba92aa0f9cac97f7626"
    )

    client = CustomClient("https://localhost:8000", mr_enclave, mr_signer)

    client.get_some_greetings()
    client.get_your_own_headers()
    client.log_some_string()
