from decimal import Decimal

# TODO: se o serviço usar GSIs com nomes diferentes de GSI1PK/GSI1SK/GSI2PK/GSI2SK
# (ver terraform-aws/dynamodb.tf), atualize esta lista de chaves internas.
INTERNAL_KEYS = {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK"}


def strip_internal_keys(item: dict | None) -> dict | None:
    """Remove as chaves de tabela/índice (PK, SK, GSI*) de um item do DynamoDB."""
    if item is None:
        return None
    return {key: value for key, value in item.items() if key not in INTERNAL_KEYS}


def normalize_number(value):
    """Converte Decimal (como o DynamoDB devolve números) em int ou float, recursivamente."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: normalize_number(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [normalize_number(nested) for nested in value]
    return value
