import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from urllib.request import Request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

Transport = Callable[[Request, float], tuple[int, bytes]]


class InternalApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


class DependencyUnavailable(Exception):
    pass


class _NetworkError(Exception):
    pass


def _urllib_transport(req: Request, timeout: float) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


class InternalApiClient:
    def __init__(
        self,
        endpoint: str | None = None,
        *,
        timeout: float = 3.0,
        transport: Transport | None = None,
        credentials=None,
        region: str | None = None,
    ):
        self._endpoint = endpoint if endpoint is not None else os.environ["INTERNAL_API_ENDPOINT"]
        self._timeout = timeout
        self._transport = transport or _urllib_transport
        self._credentials = credentials
        self._region = region

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict | None = None,
        correlation_id: str = "",
    ) -> dict | None:
        url = self._endpoint.rstrip("/") + "/" + path.lstrip("/")
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None

        status, payload = self._send_with_retry(method, url, data, correlation_id)
        if 200 <= status < 300:
            return json.loads(payload) if status != 204 and payload else None
        raise _error_from(status, payload)

    def _send_with_retry(self, method, url, data, correlation_id) -> tuple[int, bytes]:
        for _ in range(2):
            try:
                status, payload = self._send(method, url, data, correlation_id)
            except _NetworkError:
                continue
            if status < 500:
                return status, payload
        raise DependencyUnavailable("API interna indisponível.")

    def _send(self, method, url, data, correlation_id) -> tuple[int, bytes]:
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id
        aws = AWSRequest(method=method, url=url, data=data, headers=headers)
        credentials = self._credentials or boto3.Session().get_credentials()
        region = self._region or os.environ.get("AWS_REGION", "us-east-1")
        SigV4Auth(credentials, "execute-api", region).add_auth(aws)
        req = Request(url, data=data, method=method, headers=dict(aws.headers.items()))
        try:
            return self._transport(req, self._timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise _NetworkError(str(err)) from err


def _error_from(status: int, payload: bytes) -> InternalApiError:
    code, message = "UNKNOWN", ""
    try:
        error = json.loads(payload)["error"]
        code, message = str(error["code"]), str(error.get("message", ""))
    except (ValueError, KeyError, TypeError):
        pass
    return InternalApiError(status, code, message)
