from decimal import Decimal

from service_template.dynamo import normalize_number, strip_internal_keys


def test_strip_internal_keys_removes_table_and_index_keys():
    item = {"PK": "X#1", "SK": "META", "GSI1PK": "a", "GSI1SK": "b", "GSI2PK": "c", "GSI2SK": "d", "id": "1", "name": "Item"}
    assert strip_internal_keys(item) == {"id": "1", "name": "Item"}


def test_strip_internal_keys_returns_none_for_none():
    assert strip_internal_keys(None) is None


def test_normalize_number_converts_integral_decimal_to_int():
    assert normalize_number(Decimal("12")) == 12
    assert isinstance(normalize_number(Decimal("12")), int)


def test_normalize_number_converts_fractional_decimal_to_float():
    assert normalize_number(Decimal("1.5")) == 1.5


def test_normalize_number_recurses_into_dicts_and_lists():
    value = {"price": Decimal("10"), "items": [Decimal("1.5"), Decimal("2")]}
    assert normalize_number(value) == {"price": 10, "items": [1.5, 2]}
