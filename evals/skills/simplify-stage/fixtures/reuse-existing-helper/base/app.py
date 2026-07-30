def normalize(value):
    return value.strip().lower()


def normalize_all(values):
    return [normalize(value) for value in values]
