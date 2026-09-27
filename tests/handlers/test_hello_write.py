import json

import boto3
import pytest
from moto import mock_aws
from unittest.mock import MagicMock

from service_template import events
from service_template.handlers import hello_write
from handlers.api_events import http_event


@pytest.fixture
def table(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("TABLE_NAME", "test-table")
        monkeypatch.setenv("EVENT_BUS_NAME", "megamix-events")
        client = boto3.client("dynamodb", region_name="sa-east-1")
        client.create_table(
            TableName="test-table",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield boto3.resource("dynamodb", region_name="sa-east-1").Table("test-table")


@pytest.fixture(autouse=True)
def fake_events_client(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(events, "_events_client", lambda: fake_client)
    return fake_client


def test_create_hello_rejects_without_allowed_group(table, lambda_context):
    body = json.dumps({"name": "Mundo"})
    response = hello_write.handler(http_event("POST", "/hello", body=body), lambda_context)
    assert response["statusCode"] == 403


def test_create_hello_persists_item_and_publishes_events(table, lambda_context, fake_events_client, assert_no_internal_keys):
    body = json.dumps({"name": "Mundo"})
    event = http_event("POST", "/hello", body=body, groups="Vendedor", sub="user-1")

    response = hello_write.handler(event, lambda_context)

    assert response["statusCode"] == 201
    created = json.loads(response["body"])
    assert created["name"] == "Mundo"
    assert_no_internal_keys(created)

    stored = table.get_item(Key={"PK": f"HELLO#{created['id']}", "SK": "META"}).get("Item")
    assert stored["name"] == "Mundo"

    published = [call.kwargs["Entries"][0]["DetailType"] for call in fake_events_client.put_events.call_args_list]
    assert published == ["AdminActionPerformed", "HelloCreated"]


def test_create_hello_rejects_body_without_name(table, lambda_context):
    event = http_event("POST", "/hello", body=json.dumps({}), groups="Vendedor")
    response = hello_write.handler(event, lambda_context)
    assert response["statusCode"] == 400
