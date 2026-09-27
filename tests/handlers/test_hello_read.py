import json

import boto3
import pytest
from moto import mock_aws

from service_template.handlers import hello_read
from handlers.api_events import http_event


@pytest.fixture
def table(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("TABLE_NAME", "test-table")
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


def test_get_hello_returns_item_without_internal_keys(table, lambda_context, assert_no_internal_keys):
    table.put_item(Item={"PK": "HELLO#1", "SK": "META", "id": "1", "name": "Mundo"})

    response = hello_read.handler(http_event("GET", "/hello/1"), lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body == {"id": "1", "name": "Mundo"}
    assert_no_internal_keys(body)


def test_get_hello_returns_404_when_missing(table, lambda_context):
    response = hello_read.handler(http_event("GET", "/hello/missing"), lambda_context)
    assert response["statusCode"] == 404
