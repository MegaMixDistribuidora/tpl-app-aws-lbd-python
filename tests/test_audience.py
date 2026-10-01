import pytest

from service_template.audience import audience
from service_template.errors import ForbiddenError


@pytest.fixture
def api_ids(monkeypatch):
    monkeypatch.setenv("STORE_API_ID", "store1")
    monkeypatch.setenv("ADMIN_API_ID", "admin1")
    monkeypatch.setenv("INTERNAL_API_ID", "int1")


@pytest.mark.parametrize(
    "api_id,expected", [("store1", "store"), ("admin1", "admin"), ("int1", "internal")]
)
def test_resolves_audience_by_api_id(api_ids, api_id, expected):
    assert audience({"requestContext": {"apiId": api_id}}) == expected


def test_unknown_api_id_is_forbidden(api_ids):
    with pytest.raises(ForbiddenError) as exc:
        audience({"requestContext": {"apiId": "outra"}})
    assert exc.value.message == "Você não tem permissão para esta ação."


def test_empty_env_never_matches(monkeypatch):
    monkeypatch.setenv("STORE_API_ID", "")
    monkeypatch.setenv("ADMIN_API_ID", "")
    monkeypatch.setenv("INTERNAL_API_ID", "")
    with pytest.raises(ForbiddenError):
        audience({"requestContext": {"apiId": ""}})


def test_missing_request_context_is_forbidden(api_ids):
    with pytest.raises(ForbiddenError):
        audience({})
