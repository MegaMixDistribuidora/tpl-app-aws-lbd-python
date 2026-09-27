import json
import os
import uuid
from datetime import UTC, datetime

import boto3

from service_template.dynamo import strip_internal_keys

# TODO: troque "service-template" pelo nome curto do serviço (ver arquitetura.md
# §4 — Eventos de domínio: `source = megamix.<serviço>`).
EVENT_SOURCE = "megamix.service-template"

_client = None


def _events_client():
    global _client
    if _client is None:
        _client = boto3.client("events")
    return _client


def publish_admin_action(
    event: dict,
    entity: str,
    entity_id: str,
    action: str,
    before: dict | None,
    after: dict | None,
) -> None:
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    actor = claims.get("sub")
    publish_event(
        "AdminActionPerformed",
        {
            "actor": actor,
            "entity": entity,
            "entityId": entity_id,
            "action": action,
            "before": strip_internal_keys(before),
            "after": strip_internal_keys(after),
        },
    )


def publish_event(detail_type: str, data: dict, event_bus_name: str | None = None) -> None:
    bus_name = event_bus_name or os.environ["EVENT_BUS_NAME"]
    envelope = {
        "id": str(uuid.uuid4()),
        "version": 1,
        "occurredAt": datetime.now(UTC).isoformat(),
        "data": data,
    }
    _events_client().put_events(
        Entries=[
            {
                "Source": EVENT_SOURCE,
                "DetailType": detail_type,
                "Detail": json.dumps(envelope, default=str),
                "EventBusName": bus_name,
            }
        ]
    )
