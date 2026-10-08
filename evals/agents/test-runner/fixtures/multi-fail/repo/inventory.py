STOCK = {"apple": 5, "pear": 0}


def in_stock(item):
    return STOCK.get(item, 0) > 1


def reserve(item, qty):
    if STOCK.get(item, 0) < qty:
        raise ValueError(f"not enough {item}")
    STOCK[item] -= qty
    return STOCK[item]
