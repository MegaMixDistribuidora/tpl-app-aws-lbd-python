import json

import boto3
import pytest
from moto import mock_aws

from service_template.handlers import hello_manager
from handlers.api_events import http_event


def _create_table(client, name: str) -> None:
    client.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def tables(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("TABLE_NAME", "test-table")
        monkeypatch.setenv("AUDIT_TABLE_NAME", "audit-table")
        monkeypatch.setattr(hello_manager, "_client", None)
        client = boto3.client("dynamodb", region_name="sa-east-1")
        _create_table(client, "test-table")
        _create_table(client, "audit-table")
        resource = boto3.resource("dynamodb", region_name="sa-east-1")
        yield resource.Table("test-table"), resource.Table("audit-table")


@pytest.fixture
def table(tables):
    return tables[0]


def test_create_hello_rejects_without_allowed_group(table, lambda_context):
    body = json.dumps({"name": "Mundo"})
    response = hello_manager.handler(http_event("POST", "/hello", body=body), lambda_context)
    assert response["statusCode"] == 403


def test_create_hello_writes_item_audit_and_event_in_one_transaction(tables, lambda_context, assert_no_internal_keys):
    table, audit_table = tables
    body = json.dumps({"name": "Mundo"})
    event = http_event(
        "POST", "/hello", body=body, groups="Vendedor", uid="uid-1", headers={"X-Correlation-Id": "corr-1"}
    )

    response = hello_manager.handler(event, lambda_context)

    assert response["statusCode"] == 201
    created = json.loads(response["body"])
    assert created["name"] == "Mundo"
    assert_no_internal_keys(created)

    stored = table.get_item(Key={"PK": f"HELLO#{created['id']}", "SK": "META"}).get("Item")
    assert stored["name"] == "Mundo"

    outbox_items = [item for item in table.scan()["Items"] if item["PK"].startswith("EVENT#")]
    assert len(outbox_items) == 1
    assert outbox_items[0]["detailType"] == "HelloCreated"
    assert outbox_items[0]["data"] == {"helloId": created["id"]}
    assert outbox_items[0]["correlationId"] == "corr-1"

    audit_items = audit_table.scan()["Items"]
    assert len(audit_items) == 1
    assert audit_items[0]["PK"] == f"hello#{created['id']}"
    assert audit_items[0]["actorId"] == "uid-1"
    assert audit_items[0]["correlationId"] == "corr-1"
    assert audit_items[0]["changes"]["name"] == {"after": "Mundo"}


def test_create_hello_uses_request_id_when_there_is_no_correlation_header(table, lambda_context):
    event = http_event("POST", "/hello", body=json.dumps({"name": "Mundo"}), groups="Vendedor", uid="uid-1")

    hello_manager.handler(event, lambda_context)

    outbox_items = [item for item in table.scan()["Items"] if item["PK"].startswith("EVENT#")]
    assert outbox_items[0]["correlationId"] == "test-request-id"


def test_create_hello_without_uid_returns_403_and_writes_nothing(table, lambda_context):
    event = http_event("POST", "/hello", body=json.dumps({"name": "Mundo"}), groups="Vendedor")

    response = hello_manager.handler(event, lambda_context)

    assert response["statusCode"] == 403
    assert table.scan()["Items"] == []


def test_create_hello_writes_nothing_when_the_audit_write_fails(table, lambda_context, monkeypatch):
    monkeypatch.setenv("AUDIT_TABLE_NAME", "missing-audit-table")
    event = http_event("POST", "/hello", body=json.dumps({"name": "Mundo"}), groups="Vendedor", uid="uid-1")

    with pytest.raises(Exception):
        hello_manager.handler(event, lambda_context)

    assert table.scan()["Items"] == []


def test_create_hello_checks_uid_before_the_body(table, lambda_context):
    event = http_event("POST", "/hello", body=json.dumps({}), groups="Vendedor")

    response = hello_manager.handler(event, lambda_context)

    assert response["statusCode"] == 403


def test_create_hello_rejects_body_without_name(table, lambda_context):
    event = http_event("POST", "/hello", body=json.dumps({}), groups="Vendedor", uid="uid-1")
    response = hello_manager.handler(event, lambda_context)
    assert response["statusCode"] == 400


def test_get_hello_returns_item_without_internal_keys(table, lambda_context, assert_no_internal_keys):
    table.put_item(Item={"PK": "HELLO#1", "SK": "META", "id": "1", "name": "Mundo"})

    response = hello_manager.handler(http_event("GET", "/hello/1", groups="Vendedor"), lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body == {"id": "1", "name": "Mundo"}
    assert_no_internal_keys(body)


def test_get_hello_returns_404_when_missing(table, lambda_context):
    response = hello_manager.handler(http_event("GET", "/hello/missing", groups="Vendedor"), lambda_context)
    assert response["statusCode"] == 404


def test_get_hello_without_staff_group_returns_403(table, lambda_context):
    response = hello_manager.handler(http_event("GET", "/hello/1"), lambda_context)

    assert response["statusCode"] == 403
