"""
StockSense AI - ntfy.sh Push Notification Engine
------------------------------------------------
Publishes operational alerts to ntfy.sh topic or self-hosted ntfy instance:
- Low Stock alerts
- Perishable Batch Expiry (< N days)
- POS Payment Verification
- Box Scan Location Count Mismatch
- Scanner Hardware Failure
Strict privacy: Summaries only, zero customer PII.
Deduplication: Dedup cache prevents repeat notifications.
"""

import os
import logging
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger(__name__)

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "stocksense-alerts-demo")
NTFY_BASE_URL = os.environ.get("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")

# In-memory deduplication set
_SENT_DEDUP_KEYS = set()

RULE_TAGS = {
    "LOW_STOCK": ["warning", "package"],
    "EXPIRY_RISK": ["alarm_clock", "hourglass"],
    "PAYMENT_VERIFIED": ["white_check_mark", "moneybag"],
    "COUNT_MISMATCH": ["triangular_flag_on_post", "mag"],
    "SCANNER_FAILURE": ["rotating_light", "video_camera"]
}

RULE_PRIORITIES = {
    "LOW_STOCK": "high",
    "EXPIRY_RISK": "urgent",
    "PAYMENT_VERIFIED": "default",
    "COUNT_MISMATCH": "high",
    "SCANNER_FAILURE": "urgent"
}

def publish_notification(
    rule_type: str,
    title: str,
    message: str,
    dedup_key: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    timeout: int = 5
) -> Dict[str, Any]:
    """
    Publishes an alert notification to ntfy.sh.
    Returns: {"status": "sent" | "deduped" | "failed", "topic": NTFY_TOPIC, "dedup_key": dedup_key}
    """
    # 1. Deduplication Check
    if dedup_key:
        if dedup_key in _SENT_DEDUP_KEYS:
            logger.info(f"Skipping duplicate ntfy notification for key: {dedup_key}")
            return {"status": "deduped", "topic": NTFY_TOPIC, "dedup_key": dedup_key}
        _SENT_DEDUP_KEYS.add(dedup_key)

    # 2. Derive Tags & Priority
    assigned_tags = tags or RULE_TAGS.get(rule_type, ["bell"])
    assigned_priority = priority or RULE_PRIORITIES.get(rule_type, "default")

    url = f"{NTFY_BASE_URL}/{NTFY_TOPIC}"
    headers = {
        "Title": title[:200],
        "Priority": assigned_priority,
        "Tags": ",".join(assigned_tags)
    }

    try:
        response = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=timeout)
        if response.status_code in (200, 201):
            return {
                "status": "sent",
                "status_code": response.status_code,
                "topic": NTFY_TOPIC,
                "dedup_key": dedup_key
            }
        else:
            logger.warning(f"ntfy error: HTTP {response.status_code} - {response.text}")
            return {
                "status": "failed",
                "status_code": response.status_code,
                "error": response.text,
                "dedup_key": dedup_key
            }
    except Exception as e:
        logger.error(f"Failed to post to ntfy: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "dedup_key": dedup_key
        }

def clear_dedup_cache():
    """Clears in-memory dedup keys (useful for unit tests)."""
    _SENT_DEDUP_KEYS.clear()
