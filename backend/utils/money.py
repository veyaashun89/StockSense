from decimal import Decimal, ROUND_HALF_UP
from typing import Union

def rupees_to_paise(amount_in_rupees: Union[float, int, str, Decimal]) -> int:
    """
    Safely converts Rupees (or standard currency units) to integer Paise.
    Guarantees no floating point representation inaccuracy.
    Example: 108.50 -> 10850
    """
    if amount_in_rupees is None:
        return 0
    d = Decimal(str(amount_in_rupees))
    paise = (d * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise)

def paise_to_rupees(paise: Union[int, None]) -> float:
    """
    Converts integer Paise to floating point representation for API response boundaries.
    Example: 10850 -> 108.50
    """
    if paise is None:
        return 0.0
    return float(Decimal(paise) / Decimal("100"))

def calculate_gst_paise(subtotal_paise: int, gst_rate_pct: float) -> int:
    """
    Calculates exact GST amount in paise using banker's rounding to nearest paisa.
    """
    if not subtotal_paise or not gst_rate_pct:
        return 0
    rate = Decimal(str(gst_rate_pct)) / Decimal("100")
    tax = (Decimal(subtotal_paise) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(tax)
