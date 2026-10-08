from inventory import in_stock


def can_order(item):
    return in_stock(item)
