def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    """Return 0.0 if the denominator is zero, otherwise the ratio."""
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return 0.0
