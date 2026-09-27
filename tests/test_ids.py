import re

from service_template.ids import new_id, slugify


def test_new_id_is_a_valid_ulid():
    id_a = new_id()
    id_b = new_id()
    assert re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", id_a)
    assert id_a != id_b


def test_new_id_sorts_by_creation_time():
    import time

    first = new_id()
    time.sleep(0.002)
    second = new_id()
    assert first < second


def test_slugify_lowercases_and_strips_accents():
    assert slugify("Óptico Premium") == "optico-premium"


def test_slugify_collapses_separators():
    assert slugify("  Cabo  USB--C  ") == "cabo-usb-c"


def test_slugify_strips_unknown_characters():
    assert slugify("100% Algodão!") == "100-algodao"
