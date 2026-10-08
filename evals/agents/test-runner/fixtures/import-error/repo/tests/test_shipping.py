from shipping import calc_rate


def test_standard_rate():
    assert calc_rate("standard", 2) == 8.0


def test_express_rate():
    assert calc_rate("express", 0) == 15.0
