def test_upper():
    assert "a".upper() == "A"


def test_join():
    assert "-".join(["a", "b"]) == "a-b"


def test_strip():
    assert " a ".strip() == "a"
