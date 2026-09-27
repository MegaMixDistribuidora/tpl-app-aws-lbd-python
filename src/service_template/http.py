import json
from decimal import Decimal

from aws_lambda_powertools.event_handler import Response

from service_template.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError

_STATUS_BY_ERROR = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 400,
    ForbiddenError: 403,
}


def _json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"tipo não serializável: {type(value).__name__}")


def json_response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }


def parse_body(event: dict) -> dict:
    raw = event.get("body")
    if raw is None or raw == "":
        return {}
    if not isinstance(raw, str):
        raise ValidationError("corpo da requisição não é um JSON válido")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError("corpo da requisição não é um JSON válido") from exc
    if not isinstance(body, dict):
        raise ValidationError("o corpo da requisição deve ser um objeto JSON")
    return body


def error_response(exc: Exception) -> dict:
    status = _STATUS_BY_ERROR.get(type(exc), 500)
    message = exc.message if isinstance(exc, tuple(_STATUS_BY_ERROR)) else "erro interno"
    return json_response(status, {"error": message})


def api_response(status: int, body: dict) -> Response:
    result = json_response(status, body)
    return Response(status_code=result["statusCode"], content_type="application/json", body=result["body"])


def api_error_response(exc: Exception) -> Response:
    result = error_response(exc)
    return Response(status_code=result["statusCode"], content_type="application/json", body=result["body"])


def api_no_content() -> Response:
    return Response(status_code=204, content_type=None, body=None)
