RATES = {"standard": 5.0, "express": 15.0}


def rate_for(method, weight_kg):
    return RATES[method] + 1.5 * weight_kg
