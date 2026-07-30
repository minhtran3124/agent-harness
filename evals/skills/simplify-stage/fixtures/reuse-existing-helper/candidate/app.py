def normalize(value):
    return value.strip().lower()


def normalize_all(values):
    return [value.strip().lower() for value in values]
