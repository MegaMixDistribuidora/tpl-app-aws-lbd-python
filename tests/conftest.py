from dataclasses import dataclass

import pytest


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "sa-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.delenv("AWS_PROFILE", raising=False)


INTERNAL_KEYS = {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK"}


def _find_internal_keys(value, path="$"):
    found = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in INTERNAL_KEYS:
                found.append(f"{path}.{key}")
            found.extend(_find_internal_keys(nested, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_find_internal_keys(nested, f"{path}[{index}]"))
    return found


@pytest.fixture
def assert_no_internal_keys():
    def check(value):
        leaked = _find_internal_keys(value)
        assert leaked == [], f"chaves internas vazaram: {leaked}"

    return check


@dataclass
class _FakeLambdaContext:
    function_name: str = "test-function"
    memory_limit_in_mb: int = 256
    invoked_function_arn: str = "arn:aws:lambda:sa-east-1:123456789012:function:test-function"
    aws_request_id: str = "00000000-0000-0000-0000-000000000000"

    def get_remaining_time_in_millis(self) -> int:
        return 30000


@pytest.fixture
def lambda_context():
    return _FakeLambdaContext()
