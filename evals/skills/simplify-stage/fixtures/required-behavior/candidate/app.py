def square(value):
    if value < 0:
        raise ValueError("negative values are forbidden")
    return value * value
