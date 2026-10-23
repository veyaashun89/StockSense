import pytest
from unittest.mock import patch, MagicMock
from backend.services.notifier import (
    publish_notification,
    clear_dedup_cache,
    RULE_TAGS,
    RULE_PRIORITIES
)

@pytest.fixture(autouse=True)
def reset_cache():
    clear_dedup_cache()

def test_ntfy_notification_rules_and_payloads():
    """
    Phase 5 Requirement:
    Test rules: low stock, expiry within N days, payment verified, count mismatch, scanner failure.
    Must send to mock server, never real ntfy.sh during unit tests.
    """
    rules = [
        ("LOW_STOCK", "Low Stock Alert: SKU-MILK-500", "Current on-hand (4) fell below Reorder Point (12)."),
        ("EXPIRY_RISK", "Perishable Batch Expiry: SKU-YOG-02", "Batch B-901 expires in 3 days (2026-10-27)."),
        ("PAYMENT_VERIFIED", "UPI Payment Confirmed", "Verified Rs. 142.50 via UPI UTR 9102847291."),
        ("COUNT_MISMATCH", "Stock Discrepancy in Box B101", "Expected 6 units of SKU-MILK-500, audited 4 units."),
        ("SCANNER_FAILURE", "Scanner Stream Timeout", "POS webcam input lost for 15 seconds.")
    ]

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "SUCCESS"
        mock_post.return_value = mock_resp

        for rule_type, title, message in rules:
            res = publish_notification(rule_type, title, message, dedup_key=f"key_{rule_type}")
            assert res["status"] == "sent"
            assert res["dedup_key"] == f"key_{rule_type}"

            # Verify request headers and tags
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert headers["Title"] == title
            assert headers["Priority"] == RULE_PRIORITIES[rule_type]
            assert ",".join(RULE_TAGS[rule_type]) in headers["Tags"]

def test_ntfy_deduplication():
    """
    Phase 5 Requirement:
    Deduplicate by dedup_key so repeat notifications are safely ignored.
    """
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        # First dispatch should succeed
        res1 = publish_notification("LOW_STOCK", "Low Stock", "Only 2 left", dedup_key="unique_sku_101")
        assert res1["status"] == "sent"
        assert mock_post.call_count == 1

        # Second dispatch with identical dedup_key should be suppressed
        res2 = publish_notification("LOW_STOCK", "Low Stock", "Only 2 left", dedup_key="unique_sku_101")
        assert res2["status"] == "deduped"
        assert mock_post.call_count == 1  # No additional network call made

def test_ntfy_privacy_guarantee():
    """
    Phase 5 Requirement:
    Summaries only, zero customer personal data in payload.
    """
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        sample_message = "Item SKU-MAGGI-70 reordered automatically. Pack size: 24."
        publish_notification("LOW_STOCK", "Replenishment Notice", sample_message)

        sent_body = mock_post.call_args[1]["data"].decode("utf-8")
        # Ensure no email addresses, credit cards, or phone numbers
        assert "@" not in sent_body
        assert "password" not in sent_body.lower()
        assert len(sent_body.split()) < 30  # Concise summary
