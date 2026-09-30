from datetime import UTC, datetime

from service_template.dynamo_format import item_to_dynamo
from service_template.ids import new_id

# O item some depois de 48 h, mais que as 24 h de retenção do Stream (ADR-27).
TTL_SECONDS = 48 * 3600


def event_put(table: str, detail_type: str, data: dict, *, correlation_id: str, version: int = 1) -> dict:
    """`Put` de `TransactItems` com o item de evento do outbox (ADR-27), gravado na mesma
    transação da alteração. `event_publisher` o publica no bus a partir do Stream.

    `data` leva ids e o que só existe no momento do fato; nunca dado pessoal.
    `version` é a do formato do evento. O `id` é sempre novo: uma operação gera vários
    eventos, e o `correlationId` os liga."""
    now = datetime.now(UTC).replace(microsecond=0)
    event_id = new_id()
    item = {
        "PK": f"EVENT#{event_id}",
        "SK": "EVENT",
        "id": event_id,
        "detailType": detail_type,
        "version": version,
        "occurredAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "correlationId": correlation_id,
        "data": data,
        "ttl": int(now.timestamp()) + TTL_SECONDS,
    }
    return {"Put": {"TableName": table, "Item": item_to_dynamo(item), "ConditionExpression": "attribute_not_exists(PK)"}}
