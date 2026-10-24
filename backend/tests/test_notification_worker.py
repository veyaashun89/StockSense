import pytest
import time
import datetime
from unittest.mock import patch, MagicMock

from backend.app import create_app
from backend.database import init_db, get_db_session
from backend.repositories.notification_repository import NotificationRepository
from backend.workers.notification_worker import enqueue_notification, flush_queue, start_worker, stop_worker

@pytest.fixture
def app_ctx():
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        start_worker()
        yield app
        stop_worker()

def test_slow_server_does_not_block_caller(app_ctx):
    """
    Non-Negotiable Rule 1:
    A slow ntfy server must NEVER block the request thread.
    Mock server sleeps for 1.0s, but caller must return in < 150ms.
    """
    with patch("backend.services.notifier.requests.post") as mock_post:
        def slow_post(*args, **kwargs):
            time.sleep(0.8)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            return mock_resp

        mock_post.side_effect = slow_post

        start_time = time.time()
        res = enqueue_notification(
            rule="low_stock",
            title="Low Stock Test",
            message="Item low",
            priority=3,
            tags="package",
            event_ref="evt_perf_01",
            dedup_key=f"dedup_perf_{int(time.time()*1000)}",
            ignore_quiet_hours=True
        )
        elapsed = time.time() - start_time

        # Caller thread must return immediately (< 150ms)
        assert elapsed < 0.15, f"Enqueue took {elapsed:.3f}s, which is blocking!"
        assert res["status"] == "pending"

        # Allow worker thread to drain
        flush_queue()

def test_failing_server_retries_and_marks_failed(app_ctx):
    """
    Phase 3 Requirement:
    Failing ntfy server returning 500 is retried 3 times, then marked failed.
    """
    with patch("backend.services.notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        res = enqueue_notification(
            rule="low_stock",
            title="Failing Test",
            message="Server 500 test",
            priority=3,
            tags="test",
            event_ref="evt_fail_500",
            dedup_key=f"dedup_fail_{int(time.time()*1000)}",
            ignore_quiet_hours=True
        )
        assert res["status"] == "pending"
        notif_id = res["id"]

        flush_queue()

        # Verify DB status updated to 'failed' with 3 attempts
        with get_db_session() as session:
            repo = NotificationRepository(session)
            notif = repo.get_by_id(notif_id)
            assert notif.status == "failed"
            assert notif.attempts == 3
            assert "HTTP 500" in notif.last_error

def test_successful_notification_delivery(app_ctx):
    """
    Successful send updates DB record to 'sent' with sent_at timestamp.
    """
    with patch("backend.services.notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "SUCCESS"
        mock_post.return_value = mock_resp

        res = enqueue_notification(
            rule="payment_verified",
            title="Payment Received",
            message="Payment of Rs 100 received",
            priority=2,
            tags="moneybag",
            event_ref="evt_pay_01",
            dedup_key=f"dedup_pay_{int(time.time()*1000)}",
            ignore_quiet_hours=True
        )
        notif_id = res["id"]
        flush_queue()

        with get_db_session() as session:
            repo = NotificationRepository(session)
            notif = repo.get_by_id(notif_id)
            assert notif.status == "sent"
            assert notif.sent_at is not None
            assert notif.attempts == 1

def test_deduplication_suppression(app_ctx):
    """
    Duplicate notifications within the deduplication window are marked 'suppressed'.
    """
    fixed_key = f"dedup_unique_window_{int(time.time()*1000)}"

    with patch("backend.services.notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        # First dispatch
        res1 = enqueue_notification(
            rule="low_stock",
            title="Milk Low",
            message="2 left",
            priority=3,
            tags="warning",
            event_ref="evt_dup_01",
            dedup_key=fixed_key,
            ignore_quiet_hours=True
        )
        assert res1["status"] == "pending"
        flush_queue()

        # Second dispatch with identical key within window
        res2 = enqueue_notification(
            rule="low_stock",
            title="Milk Low Repeat",
            message="2 left repeat",
            priority=3,
            tags="warning",
            event_ref="evt_dup_02",
            dedup_key=fixed_key,
            ignore_quiet_hours=True
        )
        assert res2["status"] == "suppressed"
        assert res2["reason"] == "deduplicated"
        # Network post called only once!
        assert mock_post.call_count == 1

def test_quiet_hours_suppression_and_priority_5_bypass(app_ctx):
    """
    Non-urgent notifications (priority < 5) are suppressed during quiet hours.
    Priority 5 (urgent) ALWAYS bypasses quiet hours and dispatches immediately.
    """
    with patch("backend.services.notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        # Set quiet hours to cover all day (00:00 to 23:59)
        with get_db_session() as session:
            repo = NotificationRepository(session)
            repo.upsert_setting("low_stock", enabled=1, threshold=10, quiet_hours_start="00:00", quiet_hours_end="23:59")
            repo.upsert_setting("webhook_failed", enabled=1, threshold=1, quiet_hours_start="00:00", quiet_hours_end="23:59")

        # Priority 3 notification during quiet hours -> Suppressed
        res_low = enqueue_notification(
            rule="low_stock",
            title="Milk Low",
            message="Item low during quiet hours",
            priority=3,
            tags="warning",
            event_ref="evt_quiet_01",
            dedup_key=f"dedup_quiet_low_{int(time.time()*1000)}"
        )
        assert res_low["status"] == "suppressed"
        assert res_low["reason"] == "quiet_hours"

        # Priority 5 notification (webhook_failed) during quiet hours -> ALWAYS SENDS
        res_crit = enqueue_notification(
            rule="webhook_failed",
            title="Critical Webhook",
            message="Critical event",
            priority=5,
            tags="skull",
            event_ref="evt_quiet_02",
            dedup_key=f"dedup_quiet_crit_{int(time.time()*1000)}"
        )
        assert res_crit["status"] == "pending"
        flush_queue()

        with get_db_session() as session:
            repo = NotificationRepository(session)
            notif_crit = repo.get_by_id(res_crit["id"])
            assert notif_crit.status == "sent"
