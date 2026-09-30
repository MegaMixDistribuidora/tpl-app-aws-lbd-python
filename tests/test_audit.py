from boto3.dynamodb.types import TypeDeserializer

from service_template import audit

_deserializer = TypeDeserializer()


def test_diff_keeps_only_changed_fields_without_internal_keys():
    before = {"PK": "HELLO#1", "SK": "META", "id": "1", "name": "Antigo", "same": 1}
    after = {"PK": "HELLO#1", "SK": "META", "id": "1", "name": "Novo", "same": 1, "added": True}

    assert audit.diff(before, after) == {
        "name": {"before": "Antigo", "after": "Novo"},
        "added": {"after": True},
    }


def test_diff_on_creation_has_only_after():
    assert audit.diff(None, {"id": "1"}) == {"id": {"after": "1"}}


def test_audit_put_builds_item_keyed_by_entity():
    put = audit.audit_put(
        "audit-table",
        entity="hello",
        entity_id="1",
        action="created",
        actor_id="uid-1",
        correlation_id="corr-1",
        changes={"name": {"after": "Mundo"}},
    )["Put"]

    assert put["TableName"] == "audit-table"
    assert put["ConditionExpression"] == "attribute_not_exists(PK)"
    item = {key: _deserializer.deserialize(value) for key, value in put["Item"].items()}
    assert item["PK"] == "hello#1"
    assert item["SK"] == f"{item['occurredAt']}#{item['auditId']}"
    assert item["actorId"] == "uid-1"
    assert item["correlationId"] == "corr-1"
    assert item["changes"] == {"name": {"after": "Mundo"}}
