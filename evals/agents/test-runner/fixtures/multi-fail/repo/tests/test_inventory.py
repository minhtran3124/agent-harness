import inventory


def setup_function():
    inventory.STOCK.update({"apple": 5, "pear": 0, "plum": 1})


def test_in_stock_true():
    assert inventory.in_stock("apple")


def test_in_stock_single_unit():
    assert inventory.in_stock("plum")


def test_out_of_stock():
    assert not inventory.in_stock("pear")


def test_reserve_all_remaining_plum():
    assert inventory.in_stock("plum") and inventory.reserve("plum", 1) == 0
