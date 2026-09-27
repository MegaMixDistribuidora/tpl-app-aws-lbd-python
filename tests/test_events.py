import json
from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from service_template import events


def test_publish_event_sends_envelope_to_bus(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(events, "_events_client", lambda: fake_client)

    events.publish_event("HelloCreated", {"id": "hello-1"}, event_bus_name="megamix-events")

    entry = fake_client.put_events.call_args.kwargs["Entries"][0]
    assert entry["Source"] == events.EVENT_SOURCE
    assert entry["DetailType"] == "HelloCreated"
    assert entry["EventBusName"] == "megamix-events"
    detail = json.loads(entry["Detail"])
    assert detail["data"] == {"id": "hello-1"}
    assert detail["version"] == 1
    assert detail["id"] and detail["occurredAt"]


def test_publish_event_reads_bus_from_environment(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(events, "_events_client", lambda: fake_client)
    monkeypatch.setenv("EVENT_BUS_NAME", "bus-do-ambiente")

    events.publish_event("AdminActionPerformed", {"entity": "hello"})

    assert fake_client.put_events.call_args.kwargs["Entries"][0]["EventBusName"] == "bus-do-ambiente"


@mock_aws
def test_publish_event_against_moto_does_not_raise(monkeypatch):
    boto3.client("events", region_name="sa-east-1").create_event_bus(Name="megamix-events")
    monkeypatch.setattr(events, "_client", None)
    events.publish_event("HelloCreated", {"id": "hello-1"}, event_bus_name="megamix-events")


def test_publish_admin_action_uses_sub_claim_and_strips_internal_keys(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(events, "_events_client", lambda: fake_client)
    monkeypatch.setenv("EVENT_BUS_NAME", "megamix-events")

    event = {"requestContext": {"authorizer": {"jwt": {"claims": {"sub": "user-123", "email": "user@example.com"}}}}}
    before = {"PK": "HELLO#1", "SK": "META", "GSI1PK": "x", "GSI1SK": "y", "GSI2PK": "z", "GSI2SK": "w", "id": "1", "name": "Antigo"}
    after = {"PK": "HELLO#1", "SK": "META", "GSI1PK": "x", "GSI1SK": "y", "GSI2PK": "z", "GSI2SK": "w", "id": "1", "name": "Novo"}

    events.publish_admin_action(event, entity="hello", entity_id="1", action="updated", before=before, after=after)

    entry = fake_client.put_events.call_args.kwargs["Entries"][0]
    detail = json.loads(entry["Detail"])
    assert detail["data"]["actor"] == "user-123"
    assert "email" not in json.dumps(detail["data"])
    assert detail["data"]["before"] == {"id": "1", "name": "Antigo"}
    assert detail["data"]["after"] == {"id": "1", "name": "Novo"}
    assert detail["data"]["entity"] == "hello"
    assert detail["data"]["entityId"] == "1"
    assert detail["data"]["action"] == "updated"


def test_publish_admin_action_without_claims_has_none_actor(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(events, "_events_client", lambda: fake_client)
    monkeypatch.setenv("EVENT_BUS_NAME", "megamix-events")

    events.publish_admin_action({}, entity="hello", entity_id="1", action="created", before=None, after={"id": "1"})

    entry = fake_client.put_events.call_args.kwargs["Entries"][0]
    detail = json.loads(entry["Detail"])
    assert detail["data"]["actor"] is None
    assert detail["data"]["before"] is None
