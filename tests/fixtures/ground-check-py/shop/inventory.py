"""Stock keeping."""

LIMIT = 10


class Stock:
    def reserve(self, sku):
        return sku

    def release(self, sku):
        return sku


def load_stock(path):
    return Stock()
