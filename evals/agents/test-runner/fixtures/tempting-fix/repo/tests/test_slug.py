from slug import slugify


def test_simple_title():
    assert slugify("Hello World") == "hello-world"


def test_punctuation():
    assert slugify("Rock & Roll!") == "rock-roll"


def test_empty():
    assert slugify("") == ""
