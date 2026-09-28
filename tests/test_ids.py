import re
import time
import uuid

from service_template.ids import new_id, slugify

UUID7 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


def test_new_id_is_a_canonical_uuid7():
    id_a = new_id()
    id_b = new_id()
    assert UUID7.fullmatch(id_a)
    parsed = uuid.UUID(id_a)
    assert parsed.version == 7
    assert parsed.variant == uuid.RFC_4122
    assert id_a != id_b


def test_new_id_carries_the_creation_time_in_milliseconds():
    before = time.time_ns() // 1_000_000
    id_a = new_id()
    after = time.time_ns() // 1_000_000
    assert before <= uuid.UUID(id_a).int >> 80 <= after


def test_new_id_sorts_by_creation_time():
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
