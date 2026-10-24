"""
StockSense AI - Background Notification Worker
----------------------------------------------
Drains a thread-safe queue of pending notifications, dispatches them asynchronously
to ntfy with short timeout (3s) and retries with backoff (max 3), and updates delivery
status in SQLite.

Non-Negotiable Failure Design:
- Notifications are fire-and-forget.
- A slow or failing ntfy server NEVER blocks, delays, or rolls back a business transaction.
- Started on app initialization and stops cleanly on shutdown.
"""

import time
import queue
import threading
import datetime
import logging
from typing import Optional, Dict, Any

from backend.database import get_db_session
from backend.repositories.notification_repository import NotificationRepository
from backend.services.notifier import send_ntfy_request, mask_topic
from backend.services.notification_rules import (
    is_in_quiet_hours,
    is_hourly_rate_limit_exceeded,
    PRIORITY_MAX
)

logger = logging.getLogger(__name__)

_QUEUE: queue.Queue = queue.Queue(maxsize=2000)
_WORKER_THREAD: Optional[threading.Thread] = None
_STOP_EVENT: threading.Event = threading.Event()
_LOCK = threading.Lock()

def enqueue_notification(
    rule: str,
    title: str,
    message: str,
    priority: int,
    tags: Optional[str],
    event_ref: str,
    dedup_key: str,
    owner_id: int = 1,
    ignore_quiet_hours: bool = False,
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fire-and-forget enqueue method.
    Evaluates noise-control, deduplication, quiet hours, and rate limits.
    Writes audit record to database and immediately pushes to background queue.
    Takes < 5ms. NEVER blocks the caller.
    """
    now = datetime.datetime.utcnow()
    current_time_str = now.strftime("%H:%M")

    def _execute_enqueue(session):
        repo = NotificationRepository(session)

        # 1. Check Setting (Rule enabled & threshold)
        setting = repo.get_setting_by_rule(rule, owner_id=owner_id)
        if setting and setting.enabled == 0:
            notif = repo.create(
                rule=rule,
                title=title,
                message=message,
                priority=priority,
                tags=tags,
                event_ref=event_ref,
                dedup_key=dedup_key,
                status="suppressed"
            )
            notif.last_error = f"Rule '{rule}' is disabled in notification settings."
            session.flush()
            return {"status": "suppressed", "reason": "rule_disabled", "id": notif.id}

        # 2. Check Deduplication
        existing = repo.get_by_dedup_key(dedup_key)
        min_mins = setting.min_minutes_between if setting else 60
        effective_dedup_key = dedup_key
        if existing:
            time_diff = (now - existing.created_at).total_seconds() / 60.0
            if time_diff < min_mins:
                logger.info(f"Notification suppressed: duplicate key {dedup_key} within {min_mins}m window")
                return {"status": "suppressed", "reason": "deduplicated", "id": existing.id}
            else:
                effective_dedup_key = f"{dedup_key}:{int(now.timestamp())}"

        # 3. Check Quiet Hours (Priority 5 ALWAYS sends!)
        quiet_start = setting.quiet_hours_start if setting else "22:00"
        quiet_end = setting.quiet_hours_end if setting else "07:00"
        if not ignore_quiet_hours and priority < PRIORITY_MAX and is_in_quiet_hours(current_time_str, quiet_start, quiet_end):
            notif = repo.create(
                rule=rule,
                title=title,
                message=message,
                priority=priority,
                tags=tags,
                event_ref=event_ref,
                dedup_key=effective_dedup_key,
                status="suppressed"
            )
            notif.last_error = f"Suppressed during quiet hours ({quiet_start}-{quiet_end})."
            session.flush()
            logger.info(f"Notification suppressed for quiet hours ({current_time_str} in {quiet_start}-{quiet_end}): {title}")
            return {"status": "suppressed", "reason": "quiet_hours", "id": notif.id}

        # 4. Check Hourly Rate Limit (max 20 per hour per owner)
        sent_in_last_hour = repo.count_sent_in_last_hour(window_hours=1)
        if is_hourly_rate_limit_exceeded(sent_in_last_hour, max_per_hour=20):
            notif = repo.create(
                rule=rule,
                title=title,
                message=message,
                priority=priority,
                tags=tags,
                event_ref=event_ref,
                dedup_key=effective_dedup_key,
                status="suppressed"
            )
            notif.last_error = f"Hourly rate limit (20) exceeded for owner {owner_id}."
            session.flush()
            logger.warning(f"Notification rate limit exceeded: suppressed {effective_dedup_key}")
            return {"status": "suppressed", "reason": "rate_limit_exceeded", "id": notif.id}

        # 5. Passed all checks -> Create record with status='pending'
        notif = repo.create(
            rule=rule,
            title=title,
            message=message,
            priority=priority,
            tags=tags,
            event_ref=event_ref,
            dedup_key=effective_dedup_key,
            status="pending"
        )
        session.flush()
        return {"status": "pending", "id": notif.id}

    if db_session is not None:
        try:
            with db_session.begin_nested():
                result = _execute_enqueue(db_session)
        except Exception as e:
            logger.error(f"Error enqueuing notification in session savepoint: {e}")
            return {"status": "error", "error": str(e)}
    else:
        with get_db_session() as session:
            result = _execute_enqueue(session)
            session.commit()

    if result.get("status") != "pending":
        return result

    notif_id = result["id"]


    # Push to background worker queue
    queue_item = {
        "id": notif_id,
        "title": title,
        "message": message,
        "priority": priority,
        "tags": tags
    }
    try:
        _QUEUE.put_nowait(queue_item)
    except queue.Full:
        logger.error(f"Notification worker queue full! Item {notif_id} dropped from memory dispatch.")

    # Ensure worker thread is running
    ensure_worker_running()
    return {"status": "pending", "id": notif_id}

def _worker_loop():
    """Background consumer daemon draining notification queue."""
    logger.info("Notification background worker thread started.")
    while not _STOP_EVENT.is_set():
        try:
            item = _QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue

        notif_id = item["id"]
        title = item["title"]
        message = item["message"]
        priority = item["priority"]
        tags = item.get("tags")

        try:
            # Perform HTTP dispatch with 3.0s timeout and retries
            res = send_ntfy_request(
                message=message,
                title=title,
                priority=priority,
                tags=tags,
                timeout=3.0,
                max_retries=3
            )

            status = res.get("status", "failed")
            attempts = res.get("attempts", 1)
            error = res.get("error")

            # Update DB status in isolated session
            with get_db_session() as session:
                repo = NotificationRepository(session)
                sent_at = datetime.datetime.utcnow() if status == "sent" else None
                repo.update_delivery_status(
                    notification_id=notif_id,
                    status=status,
                    last_error=error,
                    sent_at=sent_at,
                    attempts=attempts
                )
        except Exception as exc:
            logger.error(f"Unexpected error in notification worker: {exc}")
            try:
                with get_db_session() as session:
                    repo = NotificationRepository(session)
                    repo.update_delivery_status(
                        notification_id=notif_id,
                        status="failed",
                        last_error=f"Worker exception: {str(exc)}",
                        attempts=1
                    )
            except Exception:
                pass
        finally:
            _QUEUE.task_done()

    logger.info("Notification background worker thread stopped.")

def start_worker():
    """Starts the background worker thread."""
    global _WORKER_THREAD, _STOP_EVENT
    with _LOCK:
        if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
            _STOP_EVENT.clear()
            _WORKER_THREAD = threading.Thread(target=_worker_loop, daemon=True, name="NotificationWorker")
            _WORKER_THREAD.start()

def ensure_worker_running():
    if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
        start_worker()

def stop_worker():
    """Stops the background worker cleanly."""
    global _STOP_EVENT, _WORKER_THREAD
    with _LOCK:
        if _WORKER_THREAD and _WORKER_THREAD.is_alive():
            _STOP_EVENT.set()
            _WORKER_THREAD.join(timeout=2.0)
            _WORKER_THREAD = None

def flush_queue(timeout: float = 5.0):
    """Waits for pending queue items to be processed."""
    _QUEUE.join()
