import pytest
import datetime
from backend.services.notification_rules import (
    evaluate_low_stock,
    evaluate_expiry_risk,
    evaluate_payment_verified,
    evaluate_count_mismatch,
    evaluate_scanner_failure,
    evaluate_webhook_failed,
    generate_dedup_key,
    is_in_quiet_hours,
    is_hourly_rate_limit_exceeded,
    PRIORITY_MIN,
    PRIORITY_LOW,
    PRIORITY_DEFAULT,
    PRIORITY_HIGH,
    PRIORITY_MAX
)
from backend.services.notifier import (
    mask_topic,
    validate_ntfy_url,
    map_priority_to_ntfy_header,
    build_ntfy_headers
)

def test_priority_mapping_and_scale():
    assert map_priority_to_ntfy_header(1) == "1"
    assert map_priority_to_ntfy_header(2) == "2"
    assert map_priority_to_ntfy_header(3) == "3"
    assert map_priority_to_ntfy_header(4) == "4"
    assert map_priority_to_ntfy_header(5) == "5"
    assert map_priority_to_ntfy_header(0) == "1"
    assert map_priority_to_ntfy_header(10) == "5"

def test_topic_secrecy_masking():
    # Never log full topic, only last 4 characters
    assert mask_topic("stocksense-secret-topic-9921") == "***9921"
    assert mask_topic("topic-xyz7") == "***xyz7"
    assert mask_topic("abcd") == "****"
    assert mask_topic("") == "****"
    assert mask_topic(None) == "****"

def test_url_security_validation():
    # HTTPS allowed
    assert validate_ntfy_url("https://ntfy.sh") is True
    assert validate_ntfy_url("https://ntfy.internal.company.com/alerts") is True

    # HTTP rejected for remote hostnames
    assert validate_ntfy_url("http://ntfy.sh") is False
    assert validate_ntfy_url("http://insecure-alerts.com") is False

    # HTTP allowed ONLY for local dev
    assert validate_ntfy_url("http://localhost:8080") is True
    assert validate_ntfy_url("http://127.0.0.1:9090") is True

def test_rule_low_stock_priorities_and_messages():
    # Stock 0 -> Priority 4 (high)
    res_zero = evaluate_low_stock("Amul Taaza Milk 500ml", "SKU-MILK-500", on_hand=0, reorder_level=12)
    assert res_zero is not None
    assert res_zero["priority"] == PRIORITY_HIGH # 4
    assert "completely out of stock" in res_zero["message"]
    assert "0 left" in res_zero["message"]

    # Stock below reorder level -> Priority 3 (default)
    res_low = evaluate_low_stock("Amul Taaza Milk 500ml", "SKU-MILK-500", on_hand=4, reorder_level=12)
    assert res_low is not None
    assert res_low["priority"] == PRIORITY_DEFAULT # 3
    assert "4 left" in res_low["message"]

    # Stock above threshold -> None
    res_ok = evaluate_low_stock("Amul Taaza Milk 500ml", "SKU-MILK-500", on_hand=20, reorder_level=12)
    assert res_ok is None

def test_rule_expiry_risk():
    # Expiring today (days <= 0) -> Priority 4
    res_today = evaluate_expiry_risk("Fresh Yogurt", "SKU-YOG-02", days_to_expiry=0)
    assert res_today is not None
    assert res_today["priority"] == PRIORITY_HIGH # 4
    assert "expires today" in res_today["message"]

    # Expiring in 3 days -> Priority 3
    res_risk = evaluate_expiry_risk("Fresh Yogurt", "SKU-YOG-02", days_to_expiry=3)
    assert res_risk is not None
    assert res_risk["priority"] == PRIORITY_DEFAULT # 3
    assert "3 day(s)" in res_risk["message"]

    # Expiring in 10 days -> None
    assert evaluate_expiry_risk("Fresh Yogurt", "SKU-YOG-02", days_to_expiry=10) is None

def test_rule_payment_verified_privacy_guarantee():
    # Rule 2: NO customer names, phone numbers, UPI IDs, UTR numbers, card details
    res = evaluate_payment_verified(
        amount_rupees_formatted="₹85.05",
        item_count=3,
        transaction_ref="TXN-20261024-ABCDEF",
        source="POS"
    )
    assert res["priority"] == PRIORITY_LOW # 2
    msg = res["message"]
    assert "₹85.05" in msg
    assert "3 item(s)" in msg
    # Check no sensitive identifiers
    assert "@" not in msg
    assert "UTR" not in msg
    assert "+91" not in msg
    assert "customer" not in msg.lower()

def test_rule_count_mismatch():
    res = evaluate_count_mismatch(
        location_name="Warehouse Bin B102",
        sku="SKU-MILK-500",
        product_name="Amul Milk",
        difference=-2,
        expected_qty=10,
        actual_qty=8
    )
    assert res is not None
    assert res["priority"] == PRIORITY_HIGH # 4
    assert "Warehouse Bin B102" in res["message"]
    assert "-2 units" in res["message"]

def test_rule_scanner_failure_threshold():
    # Needs at least 3 failures in 10 minutes
    assert evaluate_scanner_failure(1) is None
    assert evaluate_scanner_failure(2) is None
    res = evaluate_scanner_failure(3, reason="webcam disconnect")
    assert res is not None
    assert res["priority"] == PRIORITY_DEFAULT # 3
    assert "3 consecutive recognition failures" in res["message"]

def test_rule_webhook_failed_admin_only_priority_5():
    res = evaluate_webhook_failed(reason_category="INVALID_HMAC_SIGNATURE")
    assert res["priority"] == PRIORITY_MAX # 5 (bypasses quiet hours)
    assert "INVALID_HMAC_SIGNATURE" in res["message"]
    # Ensure no raw payloads
    assert "{" not in res["message"]

def test_quiet_hours_evaluation():
    # Standard quiet hours from 22:00 to 07:00
    assert is_in_quiet_hours("23:15", "22:00", "07:00") is True
    assert is_in_quiet_hours("04:30", "22:00", "07:00") is True
    assert is_in_quiet_hours("07:00", "22:00", "07:00") is False
    assert is_in_quiet_hours("14:30", "22:00", "07:00") is False

    # Daytime quiet hours e.g. 13:00 to 15:00
    assert is_in_quiet_hours("14:00", "13:00", "15:00") is True
    assert is_in_quiet_hours("16:00", "13:00", "15:00") is False

def test_hourly_rate_limit():
    assert is_hourly_rate_limit_exceeded(19, max_per_hour=20) is False
    assert is_hourly_rate_limit_exceeded(20, max_per_hour=20) is True
    assert is_hourly_rate_limit_exceeded(25, max_per_hour=20) is True
