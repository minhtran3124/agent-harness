from calc import add, subtract


def test_add():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-2, -3) == -5


def test_subtract():
    assert subtract(5, 3) == 2


def test_subtract_to_negative():
    assert subtract(3, 5) == -2
