import re

from service_template.errors import ForbiddenError


def _parse_groups(raw_groups) -> set[str]:
    if isinstance(raw_groups, (list, tuple)):
        return {str(g).strip() for g in raw_groups if str(g).strip()}
    if isinstance(raw_groups, str):
        stripped = raw_groups.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            stripped = stripped[1:-1]
        return {g for g in re.split(r"[,\s]+", stripped) if g}
    return set()


def require_group(event: dict, allowed_groups: list[str]) -> None:
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    raw_groups = claims.get("cognito:groups", "")
    caller_groups = _parse_groups(raw_groups)
    if not caller_groups.intersection(allowed_groups):
        raise ForbiddenError("grupo insuficiente para esta operação")


def _claims(event: dict) -> dict:
    return event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})


def actor_id(event: dict) -> str:
    """Autor da escrita: claim `custom:uid` do token de staff (ADR-16, ADR-23).
    Ausente (usuário Cognito sem staff vinculado) → 403."""
    uid = _claims(event).get("custom:uid")
    if not uid:
        raise ForbiddenError("Recarregue a página e tente de novo.")
    return uid


def correlation_id(event: dict) -> str:
    """Header `x-correlation-id` (sem diferenciar maiúsculas) ou, na falta, o
    `requestContext.requestId` do API Gateway (ADR-18)."""
    for name, value in (event.get("headers") or {}).items():
        if name.lower() == "x-correlation-id" and value:
            return value
    return event.get("requestContext", {}).get("requestId", "")
