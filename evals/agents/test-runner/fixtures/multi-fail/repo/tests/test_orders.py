import inventory
from orders import can_order


def setup_function():
    inventory.STOCK.update({"apple": 5, "pear": 0, "plum": 1})


def test_can_order_apple():
    assert can_order("apple")


def test_can_order_last_plum():
    assert can_order("plum")


def test_cannot_order_pear():
    assert not can_order("pear")
