import random
from idea_jam.names import generate_display_name, new_uuid


def test_generate_display_name_shape():
    rng = random.Random(0)
    name = generate_display_name(rng)
    parts = name.split("-")
    assert len(parts) == 3
    assert parts[0].isalpha()
    assert parts[1].isalpha()
    assert parts[2].isdigit()
    assert 10 <= int(parts[2]) <= 99


def test_generate_display_name_varies():
    seen = {generate_display_name(random.Random(i)) for i in range(50)}
    assert len(seen) > 1  # not all identical


def test_new_uuid_unique():
    assert new_uuid() != new_uuid()
    assert len(new_uuid()) == 36
