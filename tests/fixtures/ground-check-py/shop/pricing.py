"""Pricing helpers."""

TAX_RATE = 0.2


def apply_discount(price, pct):
    return price * (1 - pct / 100)


def format_price(value):
    return "%.2f" % value


class Cart:
    CURRENCY = "EUR"

    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def total(self):
        return sum(self.items)

    def clear(self):
        self.items = []
