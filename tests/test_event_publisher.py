import json
from unittest.mock import MagicMock

import pytest
from boto3.dynamodb.types import TypeSerializer

from service_template.handlers import event_publisher

_serializer = TypeSerializer()


def _record(sequence: str, item: dict, event_name: str = "INSERT") -> dict:
    return {
        "eventID": sequence,
        "eventName": event_name,
        "eventSource": "aws:dynamodb",
        "dynamodb": {
            "SequenceNumber": sequence,
            "Keys": {"PK": {"S": item["PK"]}, "SK": {"S": item["SK"]}},
            "NewImage": {key: _serializer.serialize(value) for key, value in item.items()},
        },
    }


def _event_item(event_id: str = "evt-1") -> dict:
    return {
        "PK": f"EVENT#{event_id}",
        "SK": "EVENT",
        "id": event_id,
        "detailType": "HelloCreated",
        "version": 1,
        "occurredAt": "2026-09-30T12:00:00Z",
        "correlationId": "corr-1",
        "data": {"helloId": "1", "tags": ["a"], "active": True},
        "ttl": 1790000000,
    }


@pytest.fixture
def events_client(monkeypatch):
    client = MagicMock()
    client.put_events.return_value = {"FailedEntryCount": 0, "Entries": [{"EventId": "x"}]}
    monkeypatch.setattr(event_publisher, "_events_client", lambda: client)
    monkeypatch.setenv("EVENT_BUS_NAME", "megamix-events")
    return client


def test_publishes_the_envelope_from_the_outbox_item(events_client, lambda_context):
    response = event_publisher.handler({"Records": [_record("1", _event_item())]}, lambda_context)

    assert response == {"batchItemFailures": []}
    entry = events_client.put_events.call_args.kwargs["Entries"][0]
    assert entry["Source"] == event_publisher.EVENT_SOURCE
    assert entry["DetailType"] == "HelloCreated"
    assert entry["EventBusName"] == "megamix-events"
    assert json.loads(entry["Detail"]) == {
        "id": "evt-1",
        "version": 1,
        "occurredAt": "2026-09-30T12:00:00Z",
        "correlationId": "corr-1",
        "data": {"helloId": "1", "tags": ["a"], "active": True},
    }


def test_ignores_records_that_are_not_new_outbox_items(events_client, lambda_context):
    entity = {"PK": "HELLO#1", "SK": "META", "id": "1"}
    records = [
        _record("1", entity),
        _record("2", _event_item(), event_name="REMOVE"),
        _record("3", _event_item(), event_name="MODIFY"),
    ]

    response = event_publisher.handler({"Records": records}, lambda_context)

    assert response == {"batchItemFailures": []}
    events_client.put_events.assert_not_called()


def test_reports_the_record_whose_event_was_rejected(events_client, lambda_context):
    events_client.put_events.side_effect = [
        {"FailedEntryCount": 0, "Entries": [{"EventId": "a"}]},
        {"FailedEntryCount": 1, "Entries": [{"ErrorCode": "InternalFailure", "ErrorMessage": "falhou"}]},
        {"FailedEntryCount": 0, "Entries": [{"EventId": "c"}]},
    ]
    records = [_record("1", _event_item("e1")), _record("2", _event_item("e2")), _record("3", _event_item("e3"))]

    response = event_publisher.handler({"Records": records}, lambda_context)

    assert response == {"batchItemFailures": [{"itemIdentifier": "2"}]}


def test_reports_the_record_when_the_bus_call_raises(events_client, lambda_context):
    events_client.put_events.side_effect = RuntimeError("sem rede")

    response = event_publisher.handler({"Records": [_record("7", _event_item())]}, lambda_context)

    assert response == {"batchItemFailures": [{"itemIdentifier": "7"}]}
