from decimal import Decimal


def to_dynamo(value):
    """Serializa um valor Python para o formato de item do cliente DynamoDB (baixo nível,
    com tipos), usado nos `TransactItems`."""
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, (int, float, Decimal)):
        return {"N": str(value)}
    if isinstance(value, dict):
        return {"M": {k: to_dynamo(v) for k, v in value.items()}}
    if isinstance(value, list):
        return {"L": [to_dynamo(v) for v in value]}
    return {"S": str(value)}


def item_to_dynamo(item: dict) -> dict:
    """Serializa cada valor de um item (dict de topo) para o formato de cliente DynamoDB."""
    return {key: to_dynamo(value) for key, value in item.items()}
