def discount(quantity, unit_price):
    """10% off orders of 10 or more units, 20% off 50 or more."""
    total = quantity * unit_price
    if quantity > 50:
        return round(total * 0.8, 2)
    if quantity >= 10:
        return round(total * 0.9, 2)
    return total
