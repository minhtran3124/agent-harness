from pricing import discount


def test_no_discount():
    assert discount(2, 10.0) == 20.0


def test_small_bulk_discount():
    assert discount(10, 10.0) == 90.0


def test_bulk_discount_at_threshold():
    assert discount(50, 10.0) == 400.0


def test_large_bulk_discount():
    assert discount(100, 10.0) == 800.0


def test_zero_quantity():
    assert discount(0, 10.0) == 0.0
