"""Entry point."""
import json
import os
from shop import pricing as pr
import shop.inventory as inv
from shop.utils import slugify as make_slug
from shop.utils import Clock
from shop.pricing import Cart


cart = Cart()


def main():
    cart.add_item(pr.apply_discount(10, 5))
    name = make_slug("Big Sale").upper()
    stock = inv.load_stock(os.getcwd())
    print(json.dumps({"total": cart.total(), "tax": pr.TAX_RATE, "cur": Cart.CURRENCY}))
    print(os.path.join("a", "b"), name, str(Clock().now()), type(stock), inv.Stock)
    return str.upper("done")
