from datetime import UTC, datetime

from boto3.dynamodb.types import TypeDeserializer

from service_template import outbox
from service_template.ids import new_id

_deserializer = TypeDeserializer()


def _plain(typed_item: dict) -> dict:
    return {key: _deserializer.deserialize(value) for key, value in typed_item.items()}


def test_event_put_builds_outbox_item_for_the_transaction():
    put = outbox.event_put("test-table", "HelloCreated", {"helloId": "1"}, correlation_id="corr-1")["Put"]

    assert put["TableName"] == "test-table"
    assert put["ConditionExpression"] == "attribute_not_exists(PK)"
    item = _plain(put["Item"])
    assert item["PK"] == f"EVENT#{item['id']}"
    assert item["SK"] == "EVENT"
    assert item["detailType"] == "HelloCreated"
    assert item["version"] == 1
    assert item["correlationId"] == "corr-1"
    assert item["data"] == {"helloId": "1"}


def test_event_put_uses_a_new_uuidv7_per_event_not_the_correlation_id():
    first = _plain(outbox.event_put("t", "HelloCreated", {}, correlation_id="corr-1")["Put"]["Item"])
    second = _plain(outbox.event_put("t", "HelloCreated", {}, correlation_id="corr-1")["Put"]["Item"])

    assert first["id"] != second["id"]
    assert first["id"] != "corr-1"
    assert len(first["id"]) == len(new_id()) and first["id"][14] == "7"


def test_event_put_expires_after_48_hours():
    item = _plain(outbox.event_put("t", "HelloCreated", {}, correlation_id="c")["Put"]["Item"])

    occurred_at = datetime.strptime(item["occurredAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert int(item["ttl"]) == int(occurred_at.timestamp()) + 48 * 3600


def test_event_put_accepts_explicit_version():
    item = _plain(outbox.event_put("t", "HelloCreated", {}, correlation_id="c", version=2)["Put"]["Item"])
    assert item["version"] == 2
