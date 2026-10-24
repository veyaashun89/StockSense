"""
StockSense AI - Notification Rules Engine
-----------------------------------------
Decides which events produce notifications, applying thresholds, noise control,
deduplication keys, quiet hours, and rate limits.

Non-Negotiable Privacy:
Never include customer names, phone numbers, UPI IDs, UTR numbers, card details,
or full addresses in notification titles or messages. Summaries only.
"""

import datetime
from typing import Optional, Dict, Any, Tuple

# Priority Scale according to ntfy.sh documentation (https://docs.ntfy.sh/publish/#message-priority)
# 1: min, 2: low, 3: default, 4: high, 5: max/urgent
PRIORITY_MIN = 1
PRIORITY_LOW = 2
PRIORITY_DEFAULT = 3
PRIORITY_HIGH = 4
PRIORITY_MAX = 5

DEFAULT_RULE_TAGS = {
    "low_stock": "warning,package",
    "expiry_risk": "alarm_clock,hourglass",
    "payment_verified": "white_check_mark,moneybag",
    "count_mismatch": "triangular_flag_on_post,mag",
    "scanner_failure": "rotating_light,video_camera",
    "webhook_failed": "rotating_light,skull"
}

def generate_dedup_key(
    rule: str,
    product_id: Optional[Any] = None,
    location_id: Optional[Any] = None,
    date_bucket: Optional[str] = None,
    extra_suffix: Optional[str] = None
) -> str:
    """
    Standardized dedup_key builder:
    dedup_key = rule + product_id + location_id + date-bucket
    """
    bucket = date_bucket or datetime.date.today().isoformat()
    pid = str(product_id) if product_id is not None else "0"
    lid = str(location_id) if location_id is not None else "0"
    parts = [rule, pid, lid, bucket]
    if extra_suffix:
        parts.append(str(extra_suffix))
    return ":".join(parts)

def is_in_quiet_hours(time_str: str, quiet_start: str, quiet_end: str) -> bool:
    """
    Checks if a given time "HH:MM" falls within quiet hours [quiet_start, quiet_end].
    Correctly handles midnight wrap-around (e.g. 22:00 to 07:00).
    """
    if not quiet_start or not quiet_end or quiet_start == quiet_end:
        return False

    try:
        def to_mins(t_str: str) -> int:
            h, m = map(int, t_str.strip().split(":"))
            return h * 60 + m

        curr = to_mins(time_str)
        start = to_mins(quiet_start)
        end = to_mins(quiet_end)

        if start <= end:
            return start <= curr < end
        else:
            # Wraps around midnight (e.g. 22:00 to 07:00)
            return curr >= start or curr < end
    except Exception:
        return False

def is_hourly_rate_limit_exceeded(sent_in_last_hour: int, max_per_hour: int = 20) -> bool:
    """
    Rate limit: no more than 20 notifications per hour per owner.
    """
    return sent_in_last_hour >= max_per_hour

# -------------------------------------------------------------------------
# Rule Evaluators (Pure Functions)
# -------------------------------------------------------------------------

def evaluate_low_stock(
    product_name: str,
    sku: str,
    on_hand: int,
    reorder_level: int,
    location_name: str = "Store-1",
    product_id: Optional[int] = None,
    location_id: Optional[int] = None,
    threshold: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Rule: low_stock
    - priority 4 when stock is 0
    - priority 3 when below reorder level (or configured threshold)
    """
    effective_thresh = int(threshold) if threshold is not None else reorder_level
    if on_hand > effective_thresh:
        return None

    if on_hand == 0:
        priority = PRIORITY_HIGH # 4
        title = f"Stockout Alert: {product_name[:30]}"
        message = f"{product_name} ({sku}) is completely out of stock (0 left at {location_name})."
    else:
        priority = PRIORITY_DEFAULT # 3
        title = f"Low Stock: {product_name[:30]}"
        message = f"{product_name} ({sku}) low: {on_hand} left at {location_name} (reorder point: {effective_thresh})."

    dedup_key = generate_dedup_key("low_stock", product_id=product_id or sku, location_id=location_id)

    return {
        "rule": "low_stock",
        "title": title,
        "message": message,
        "priority": priority,
        "tags": DEFAULT_RULE_TAGS["low_stock"],
        "dedup_key": dedup_key
    }

def evaluate_expiry_risk(
    product_name: str,
    sku: str,
    days_to_expiry: int,
    batch_ref: Optional[str] = None,
    location_name: str = "Store-1",
    product_id: Optional[int] = None,
    threshold_days: float = 3.0
) -> Optional[Dict[str, Any]]:
    """
    Rule: expiry_risk
    - priority 3 within the window (e.g. <= 3 days)
    - priority 4 when expiring today (days <= 0)
    """
    if days_to_expiry > threshold_days:
        return None

    if days_to_expiry <= 0:
        priority = PRIORITY_HIGH # 4
        title = f"Expiring Today: {product_name[:30]}"
        message = f"Batch for {product_name} ({sku}) expires today at {location_name}. Action required."
    else:
        priority = PRIORITY_DEFAULT # 3
        title = f"Expiry Risk: {product_name[:30]}"
        message = f"{product_name} ({sku}) expires in {days_to_expiry} day(s) at {location_name}."

    dedup_key = generate_dedup_key("expiry_risk", product_id=product_id or sku, extra_suffix=batch_ref or "batch")

    return {
        "rule": "expiry_risk",
        "title": title,
        "message": message,
        "priority": priority,
        "tags": DEFAULT_RULE_TAGS["expiry_risk"],
        "dedup_key": dedup_key
    }

def evaluate_payment_verified(
    amount_rupees_formatted: str,
    item_count: int,
    transaction_ref: str,
    source: str = "POS"
) -> Dict[str, Any]:
    """
    Rule: payment_verified
    - priority 2 (informational)
    - Non-negotiable: NO customer names, phone numbers, UPI IDs, UTR numbers, or card details!
    """
    title = "Payment Confirmed"
    message = f"Received {amount_rupees_formatted} for {item_count} item(s) via {source}."
    dedup_key = generate_dedup_key("payment_verified", extra_suffix=transaction_ref)

    return {
        "rule": "payment_verified",
        "title": title,
        "message": message,
        "priority": PRIORITY_LOW, # 2
        "tags": DEFAULT_RULE_TAGS["payment_verified"],
        "dedup_key": dedup_key
    }

def evaluate_count_mismatch(
    location_name: str,
    sku: str,
    product_name: str,
    difference: int,
    expected_qty: int,
    actual_qty: int,
    location_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Rule: count_mismatch
    - priority 4
    - Includes location name and the difference
    """
    if difference == 0:
        return None

    diff_str = f"+{difference}" if difference > 0 else f"{difference}"
    title = f"Count Mismatch: {location_name}"
    message = f"Discrepancy at {location_name}: {product_name} ({sku}) diff {diff_str} units (audited {actual_qty} vs expected {expected_qty})."
    dedup_key = generate_dedup_key("count_mismatch", product_id=sku, location_id=location_id or location_name)

    return {
        "rule": "count_mismatch",
        "title": title,
        "message": message,
        "priority": PRIORITY_HIGH, # 4
        "tags": DEFAULT_RULE_TAGS["count_mismatch"],
        "dedup_key": dedup_key
    }

def evaluate_scanner_failure(
    failure_count_in_10m: int,
    reason: str = "Hardware timeout",
    terminal_id: str = "Register-1"
) -> Optional[Dict[str, Any]]:
    """
    Rule: scanner_failure
    - priority 3
    - ONLY after 3 failures in 10 minutes
    """
    if failure_count_in_10m < 3:
        return None

    title = "POS Scanner Alert"
    message = f"Scanner issue at {terminal_id}: {failure_count_in_10m} consecutive recognition failures ({reason}). Operator check advised."
    dedup_key = generate_dedup_key("scanner_failure", extra_suffix=f"{terminal_id}_{int(datetime.datetime.now().timestamp() // 600)}")

    return {
        "rule": "scanner_failure",
        "title": title,
        "message": message,
        "priority": PRIORITY_DEFAULT, # 3
        "tags": DEFAULT_RULE_TAGS["scanner_failure"],
        "dedup_key": dedup_key
    }

def evaluate_webhook_failed(
    reason_category: str,
    gateway: str = "PaymentGateway"
) -> Dict[str, Any]:
    """
    Rule: webhook_failed
    - priority 5 (max / urgent, bypasses quiet hours!)
    - Admin role only
    - Includes reason category, NEVER raw payload or secrets!
    """
    sanitized_reason = reason_category.replace("\n", " ").strip()[:80]
    title = "Critical: Webhook Verification Failed"
    message = f"Security Alert: Incoming {gateway} webhook rejected. Reason category: {sanitized_reason}."
    dedup_key = generate_dedup_key("webhook_failed", extra_suffix=f"{gateway}_{int(datetime.datetime.now().timestamp() // 300)}")

    return {
        "rule": "webhook_failed",
        "title": title,
        "message": message,
        "priority": PRIORITY_MAX, # 5
        "tags": DEFAULT_RULE_TAGS["webhook_failed"],
        "dedup_key": dedup_key
    }
