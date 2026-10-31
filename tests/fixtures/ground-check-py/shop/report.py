"""Report builder."""
from shop import pricing
from shop.inventory import Stock


def build():
    stock = Stock()
    stock.reserve("a")
    stock.release("a")
    return pricing.format_price(1)
