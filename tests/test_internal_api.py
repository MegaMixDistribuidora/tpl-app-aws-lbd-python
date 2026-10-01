import json
import urllib.error

import pytest
from botocore.credentials import Credentials

from service_template.internal_api import (
    DependencyUnavailable,
    InternalApiClient,
    InternalApiError,
)


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, req, timeout):
        self.calls.append((req, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make(*responses, endpoint="https://x.example/"):
    transport = FakeTransport(*responses)
    client = InternalApiClient(
        endpoint,
        transport=transport,
        credentials=Credentials("AKID", "SECRET"),
        region="sa-east-1",
    )
    return client, transport


def ok(body=None):
    return 200, json.dumps(body if body is not None else {"ok": True}).encode()


def test_signs_request_with_sigv4():
    client, t = make(ok())
    client.request("GET", "/catalog/products")
    auth = t.calls[0][0].get_header("Authorization")
    assert auth.startswith("AWS4-HMAC-SHA256")
    assert "execute-api" in auth


def test_joins_endpoint_and_path_without_double_slash():
    client, t = make(ok())
    client.request("GET", "/catalog/products")
    assert t.calls[0][0].full_url == "https://x.example/catalog/products"


def test_query_is_sent_and_signed():
    client, t = make(ok())
    client.request("GET", "/catalog/products", query={"ids": "a,b"})
    req = t.calls[0][0]
    assert req.full_url.endswith("?ids=a%2Cb")
    assert req.get_header("Authorization")


def test_propagates_correlation_id():
    client, t = make(ok())
    client.request("GET", "/p", correlation_id="c-1")
    assert t.calls[0][0].get_header("X-correlation-id") == "c-1"


def test_sends_json_body_with_content_type():
    client, t = make(ok())
    client.request("POST", "/p", body={"a": 1})
    req = t.calls[0][0]
    assert req.get_method() == "POST"
    assert json.loads(req.data) == {"a": 1}
    assert req.get_header("Content-type") == "application/json"


def test_returns_json_on_2xx_and_none_on_204():
    client, _ = make(ok({"a": 1}), (204, b""))
    assert client.request("GET", "/p") == {"a": 1}
    assert client.request("GET", "/p") is None


def test_4xx_raises_with_code_and_is_not_retried():
    body = json.dumps({"error": {"code": "NOT_FOUND", "message": "x"}}).encode()
    client, t = make((404, body))
    with pytest.raises(InternalApiError) as exc:
        client.request("GET", "/p")
    assert (exc.value.status, exc.value.code, exc.value.message) == (404, "NOT_FOUND", "x")
    assert len(t.calls) == 1


def test_4xx_outside_contract_has_unknown_code():
    client, t = make((400, b"<html>bad</html>"))
    with pytest.raises(InternalApiError) as exc:
        client.request("GET", "/p")
    assert exc.value.status == 400
    assert exc.value.code == "UNKNOWN"
    assert len(t.calls) == 1


def test_retries_once_on_5xx_then_succeeds():
    client, t = make((503, b""), ok({"a": 1}))
    assert client.request("GET", "/p") == {"a": 1}
    assert len(t.calls) == 2


def test_5xx_twice_raises_dependency_unavailable():
    client, t = make((500, b""), (502, b""))
    with pytest.raises(DependencyUnavailable):
        client.request("GET", "/p")
    assert len(t.calls) == 2


def test_network_error_twice_raises_dependency_unavailable():
    err = urllib.error.URLError("down")
    client, t = make(err, err)
    with pytest.raises(DependencyUnavailable):
        client.request("GET", "/p")
    assert len(t.calls) == 2


def test_timeout_error_is_retried_once():
    client, t = make(TimeoutError(), ok())
    assert client.request("GET", "/p") == {"ok": True}
    assert len(t.calls) == 2


def test_timeout_passed_to_transport():
    client, t = make(ok())
    client.request("GET", "/p")
    assert t.calls[0][1] == 3.0


def test_query_encodes_space_as_percent20_and_signs_same_url(monkeypatch):
    from botocore.auth import SigV4Auth

    signed_urls = []
    original = SigV4Auth.add_auth

    def spy(self, request):
        signed_urls.append(request.url)
        return original(self, request)

    monkeypatch.setattr(SigV4Auth, "add_auth", spy)
    client, t = make(ok())
    client.request("GET", "/p", query={"q": "a b/c,d"})
    sent = t.calls[0][0].full_url
    assert sent.endswith("?q=a%20b%2Fc%2Cd")
    assert signed_urls == [sent]
