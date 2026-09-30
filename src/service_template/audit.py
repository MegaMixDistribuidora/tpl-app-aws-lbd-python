from datetime import UTC, datetime

from service_template.dynamo_format import item_to_dynamo
from service_template.ids import new_id

# Chaves internas e metadados que nunca aparecem em `changes` (ADR-16).
# TODO: acrescente os GSIs reais do serviço (ver dynamo.py).
_INTERNAL_KEYS = {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "version", "createdAt", "updatedAt", "updatedBy"}


def diff(before: dict | None, after: dict | None) -> dict:
    """Só os campos alterados, `{campo: {before, after}}`, sem chaves internas."""
    before = {k: v for k, v in (before or {}).items() if k not in _INTERNAL_KEYS}
    after = {k: v for k, v in (after or {}).items() if k not in _INTERNAL_KEYS}
    result = {}
    for field in {*before, *after}:
        if field in before and field in after and before[field] == after[field]:
            continue
        entry = {}
        if field in before:
            entry["before"] = before[field]
        if field in after:
            entry["after"] = after[field]
        result[field] = entry
    return result


def audit_put(
    table: str,
    *,
    entity: str,
    entity_id: str,
    action: str,
    actor_id: str,
    correlation_id: str,
    changes: dict,
) -> dict:
    """`Put` de `TransactItems` na tabela `audit` da plataforma (ADR-16), gravado na mesma
    transação da alteração. Dado pessoal em `changes` vai mascarado; senha, nunca."""
    occurred_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    audit_id = new_id()
    item = {
        "PK": f"{entity}#{entity_id}",
        "SK": f"{occurred_at}#{audit_id}",
        "auditId": audit_id,
        "entity": entity,
        "entityId": entity_id,
        "action": action,
        "actorId": actor_id,
        "occurredAt": occurred_at,
        "correlationId": correlation_id,
        "changes": changes,
    }
    return {"Put": {"TableName": table, "Item": item_to_dynamo(item), "ConditionExpression": "attribute_not_exists(PK)"}}
