import re


def slugify(title):
    # Lowercase, then collapse every run of non-alphanumerics into one hyphen.
    text = title.upper()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")
