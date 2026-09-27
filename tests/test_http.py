import json

import pytest

from service_template.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from service_template.http import api_error_response, api_no_content, api_response, error_response, json_response, parse_body


def test_json_response_serializes_body_and_sets_status():
    result = json_response(200, {"ok": True})
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"ok": True}
    assert result["headers"]["Content-Type"] == "application/json"


def test_parse_body_decodes_json_string():
    event = {"body": '{"name": "Produto"}'}
    assert parse_body(event) == {"name": "Produto"}


def test_parse_body_returns_empty_dict_when_missing():
    assert parse_body({}) == {}


def test_parse_body_raises_validation_error_on_invalid_json():
    with pytest.raises(ValidationError):
        parse_body({"body": "{not json"})


@pytest.mark.parametrize(
    "exc,status",
    [
        (NotFoundError("produto não encontrado"), 404),
        (ConflictError("slug em uso"), 409),
        (ValidationError("campo obrigatório"), 400),
        (ForbiddenError("grupo insuficiente"), 403),
        (RuntimeError("boom"), 500),
    ],
)
def test_error_response_maps_exception_to_status(exc, status):
    result = error_response(exc)
    assert result["statusCode"] == status


def test_json_response_serializes_decimal_as_number():
    from decimal import Decimal

    result = json_response(200, {"inteiro": Decimal("12"), "fracao": Decimal("1.5")})
    assert json.loads(result["body"]) == {"inteiro": 12, "fracao": 1.5}
    assert '"inteiro": 12' in result["body"]


@pytest.mark.parametrize("raw", ["[1, 2]", '"texto"', "42", "null"])
def test_parse_body_rejects_non_object_json(raw):
    with pytest.raises(ValidationError):
        parse_body({"body": raw})


def test_parse_body_rejects_non_string_body():
    with pytest.raises(ValidationError):
        parse_body({"body": {"name": "x"}})


def test_api_response_returns_a_response_object_with_serialized_body():
    result = api_response(201, {"id": "prod-1"})
    assert result.status_code == 201
    assert result.content_type == "application/json"
    assert result.body == '{"id": "prod-1"}'


def test_api_error_response_maps_domain_error_to_status():
    from service_template.errors import ConflictError

    result = api_error_response(ConflictError("slug em uso"))
    assert result.status_code == 409
    assert "slug em uso" in result.body


def test_api_no_content_returns_204_without_body():
    result = api_no_content()
    assert result.status_code == 204
    assert result.body is None
