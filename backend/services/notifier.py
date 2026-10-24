"""
StockSense AI - ntfy.sh Push Notification Dispatcher
----------------------------------------------------
Reference Documentation:
- Documented ntfy Features: https://docs.ntfy.sh/publish/
- Headers: Title, Priority, Tags, Authorization
- Priority Scale: 1 (min) to 5 (urgent / max)
- Body: raw UTF-8 text message

Non-Negotiable Rules:
1. Topic secrecy: NTFY_TOPIC is stored in env var, never logged in full, only last 4 chars (***XXXX).
2. URL validation: HTTPS required (http allowed only for localhost/127.0.0.1 in dev/testing).
3. Short timeout: 3.0 seconds max per request.
4. Retry logic: max 3 attempts with exponential backoff on 5xx/connection errors.
   Never retry on 4xx except 429 (obeying Retry-After).
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

DEFAULT_NTFY_BASE_URL = "https://ntfy.sh"
DEFAULT_TIMEOUT_SECONDS = 3.0
MAX_RETRIES = 3

def get_ntfy_base_url() -> str:
    return os.environ.get("NTFY_BASE_URL", DEFAULT_NTFY_BASE_URL).rstrip("/")

def get_ntfy_topic() -> str:
    return os.environ.get("NTFY_TOPIC", "stocksense-ops-alerts-default")

def get_ntfy_token() -> Optional[str]:
    tok = os.environ.get("NTFY_TOKEN", "").strip()
    return tok if tok else None

def mask_topic(topic: Optional[str]) -> str:
    """
    Treat the topic as a secret. Anyone who knows it can read the messages.
    Do not log the full topic, only its last 4 characters (e.g. ***8f4b).
    """
    if not topic:
        return "****"
    cleaned = str(topic).strip()
    if len(cleaned) <= 4:
        return "****"
    return f"***{cleaned[-4:]}"

def validate_ntfy_url(url_or_base: str) -> bool:
    """
    Use HTTPS only. Reject http:// except to localhost / 127.0.0.1 in development/testing.
    """
    try:
        parsed = urlparse(url_or_base)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()

        if scheme == "https":
            return True
        if scheme == "http" and host in ("localhost", "127.0.0.1", "::1", "testserver"):
            return True
        return False
    except Exception:
        return False

def map_priority_to_ntfy_header(priority: Any) -> str:
    """
    Maps 1-5 integer or named priority to ntfy priority header value:
    1 / min, 2 / low, 3 / default, 4 / high, 5 / urgent (max)
    Documented at https://docs.ntfy.sh/publish/#message-priority
    """
    if isinstance(priority, str):
        cleaned = priority.lower().strip()
        if cleaned in ("min", "low", "default", "high", "urgent", "max", "1", "2", "3", "4", "5"):
            return cleaned
        try:
            p = int(cleaned)
            return str(max(1, min(5, p)))
        except ValueError:
            return "3"
    try:
        p = max(1, min(5, int(priority)))
        return str(p)
    except Exception:
        return "3"

def build_ntfy_headers(
    title: str,
    priority: Any = 3,
    tags: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, str]:
    """
    Builds clean, sanitized HTTP headers for ntfy.sh POST request.
    """
    headers = {
        "Title": title.encode("ascii", "ignore").decode("ascii")[:200] if not title.isascii() else title[:200],
        "Priority": map_priority_to_ntfy_header(priority),
    }
    if tags:
        headers["Tags"] = tags.strip()
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers

def send_ntfy_request(
    message: str,
    title: str,
    priority: int = 3,
    tags: Optional[str] = None,
    base_url: Optional[str] = None,
    topic: Optional[str] = None,
    token: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = MAX_RETRIES
) -> Dict[str, Any]:
    """
    Sends notification message to ntfy server with timeout and exponential backoff retries.
    Returns dictionary with execution results.
    """
    target_base = (base_url or get_ntfy_base_url()).rstrip("/")
    target_topic = topic or get_ntfy_topic()
    target_token = token if token is not None else get_ntfy_token()

    if not validate_ntfy_url(target_base):
        err = f"Security Violation: Insecure HTTP rejected for non-localhost URL ({target_base}). HTTPS required."
        logger.error(err)
        return {
            "status": "failed",
            "error": err,
            "masked_topic": mask_topic(target_topic),
            "attempts": 0
        }

    url = f"{target_base}/{target_topic}"
    headers = build_ntfy_headers(title=title, priority=priority, tags=tags, token=target_token)
    payload_bytes = message.encode("utf-8")

    attempts = 0
    last_error = None
    masked = mask_topic(target_topic)

    for attempt in range(1, max_retries + 1):
        attempts = attempt
        try:
            logger.info(f"Dispatching notification attempt {attempt}/{max_retries} to ntfy topic {masked} (priority: {priority})")
            resp = requests.post(url, data=payload_bytes, headers=headers, timeout=timeout)

            # Success
            if resp.status_code in (200, 201):
                logger.info(f"Notification successfully delivered to {masked} (HTTP {resp.status_code})")
                return {
                    "status": "sent",
                    "status_code": resp.status_code,
                    "masked_topic": masked,
                    "attempts": attempts,
                    "error": None
                }

            # Rate limited by ntfy server: check Retry-After
            if resp.status_code == 429:
                retry_after_hdr = resp.headers.get("Retry-After")
                wait_sec = min(3.0, float(retry_after_hdr)) if retry_after_hdr and retry_after_hdr.isdigit() else 1.0
                logger.warning(f"ntfy rate-limited (429) on topic {masked}; backing off {wait_sec}s")
                time.sleep(wait_sec)
                last_error = f"HTTP 429: Rate limited by ntfy server ({resp.text[:100]})"
                continue

            # Non-429 4xx errors: Client error -> NEVER RETRY
            if 400 <= resp.status_code < 500:
                err_msg = f"ntfy client error HTTP {resp.status_code}: {resp.text[:120]}"
                logger.warning(f"Permanent delivery failure on topic {masked}: {err_msg}")
                return {
                    "status": "failed",
                    "status_code": resp.status_code,
                    "masked_topic": masked,
                    "attempts": attempts,
                    "error": err_msg
                }

            # 5xx Server errors: eligible for retry with backoff
            last_error = f"ntfy server error HTTP {resp.status_code}: {resp.text[:100]}"
            logger.warning(f"Server error on attempt {attempt}: {last_error}")

        except requests.RequestException as e:
            last_error = f"Network/Timeout exception: {str(e)}"
            logger.warning(f"Connection failure to ntfy on attempt {attempt}: {last_error}")

        # Exponential backoff between retries (0.3s, 0.6s, etc.)
        if attempt < max_retries:
            time.sleep(0.3 * (2 ** (attempt - 1)))

    return {
        "status": "failed",
        "status_code": None,
        "masked_topic": masked,
        "attempts": attempts,
        "error": last_error
    }


# -------------------------------------------------------------------------
# Legacy Compatibility Interface for Existing Tests
# -------------------------------------------------------------------------
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

def clear_dedup_cache():
    _SENT_DEDUP_KEYS.clear()

def publish_notification(
    rule_type: str,
    title: str,
    message: str,
    dedup_key: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    timeout: int = 3
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for existing unit tests.
    """
    if dedup_key and dedup_key in _SENT_DEDUP_KEYS:
        return {"status": "deduped", "topic": get_ntfy_topic(), "dedup_key": dedup_key}

    if dedup_key:
        _SENT_DEDUP_KEYS.add(dedup_key)

    p_val = priority or RULE_PRIORITIES.get(rule_type, "default")
    t_str = ",".join(tags) if tags else ",".join(RULE_TAGS.get(rule_type, ["bell"]))

    res = send_ntfy_request(
        message=message,
        title=title,
        priority=p_val,
        tags=t_str,
        timeout=float(timeout)
    )
    res["dedup_key"] = dedup_key
    res["topic"] = get_ntfy_topic()
    return res
