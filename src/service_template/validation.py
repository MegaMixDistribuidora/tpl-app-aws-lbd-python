"""Helpers genéricos de validação do corpo das escritas.

TODO: adicione aqui as funções `*_fields` específicas do domínio do serviço
(um exemplo completo — validação de produto, categoria, marca — está em
aws-megamix-app-lbd-catalog-service/src/catalog_service/validation.py).
"""

import re

from service_template.errors import ValidationError

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def require_object(body) -> dict:
    if not isinstance(body, dict):
        raise ValidationError("o corpo da requisição deve ser um objeto JSON")
    return body


def required_str(body: dict, field: str) -> str:
    value = body.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} é obrigatório e deve ser um texto não vazio")
    return value


def optional_str(body: dict, field: str) -> str | None:
    value = body.get(field)
    if value is not None and not isinstance(value, str):
        raise ValidationError(f"{field} deve ser um texto ou nulo")
    return value


def optional_id(body: dict, field: str) -> str | None:
    if body.get(field) is None:
        return None
    return required_str(body, field)


def slug(body: dict) -> str:
    value = required_str(body, "slug")
    if not _SLUG_PATTERN.match(value):
        raise ValidationError("slug deve conter apenas letras minúsculas, números e hífens simples")
    return value
