"""Small helpers."""
import time


def slugify(text):
    return text.lower().replace(" ", "-")


def parse_sku(raw):
    return raw.strip()


class Clock:
    def now(self):
        return time.time()
