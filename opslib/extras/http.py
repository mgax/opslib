import json
from http import HTTPStatus

import requests

from opslib.results import OperationError, Result


def get_response_json(response):
    json_header = response.headers.get("Content-Type") == "application/json"
    has_content = response.status_code != HTTPStatus.NO_CONTENT

    if json_header and has_content:
        return response.json()


class HttpResult(Result):
    def __init__(self, response, failed=False):
        self.response = response
        self.json = get_response_json(response)

        if self.json:
            output = json.dumps(self.json, indent=2)

        else:
            output = response.text

        if failed:
            request = response.request
            output = (
                f"API error {response.status_code} "
                f"{request.method} {request.url}\n{output}"
            )

        super().__init__(
            changed=True,
            output=output,
            failed=failed,
        )


class HttpClient:
    def __init__(self, endpoint, auth=None, headers=None):
        self.endpoint = endpoint
        self.session = requests.Session()
        if auth:
            self.session.auth = auth
        self.headers = headers or {}

    def request(self, method, url, **kwargs):
        kwargs["headers"] = dict(self.headers, **kwargs.pop("headers", {}))
        response = self.session.request(method, self.endpoint + url, **kwargs)

        try:
            response.raise_for_status()

        except requests.HTTPError:
            raise OperationError(
                "API call failed", result=HttpResult(response, failed=True)
            )

        else:
            return HttpResult(response)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)
