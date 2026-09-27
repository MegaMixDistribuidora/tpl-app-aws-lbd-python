import pytest

from service_template.auth import require_group
from service_template.errors import ForbiddenError


def event_with_groups(groups: str | None):
    if groups is None:
        return {"requestContext": {"authorizer": {"jwt": {"claims": {}}}}}
    return {"requestContext": {"authorizer": {"jwt": {"claims": {"cognito:groups": groups}}}}}


def test_require_group_allows_matching_group():
    require_group(event_with_groups("Administrador"), allowed_groups=["Administrador"])


def test_require_group_allows_one_of_several_claimed_groups():
    require_group(event_with_groups("Vendedor,Administrador"), allowed_groups=["Administrador"])


def test_require_group_rejects_missing_group():
    with pytest.raises(ForbiddenError):
        require_group(event_with_groups("Vendedor"), allowed_groups=["Administrador"])


def test_require_group_rejects_absent_claims():
    with pytest.raises(ForbiddenError):
        require_group(event_with_groups(None), allowed_groups=["Vendedor"])


@pytest.mark.parametrize(
    "groups",
    [
        "[Vendedor Administrador]",
        "[Administrador]",
        ["Vendedor", "Administrador"],
    ],
)
def test_require_group_allows_api_http_authorizer_array_shapes(groups):
    require_group(event_with_groups(groups), allowed_groups=["Administrador"])


def test_require_group_rejects_bracketed_string_without_required_group():
    with pytest.raises(ForbiddenError):
        require_group(event_with_groups("[Vendedor Estoquista]"), allowed_groups=["Administrador"])
