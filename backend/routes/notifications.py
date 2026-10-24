import re
import time
import uuid
import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify

from backend.database import get_db_session
from backend.models.orm_models import Notification, NotificationSetting
from backend.repositories.notification_repository import NotificationRepository
from backend.services.notifier import get_ntfy_base_url, get_ntfy_topic, mask_topic
from backend.workers.notification_worker import enqueue_notification
from backend.services.auth_service import get_current_user_context

notifications_bp = Blueprint("notifications", __name__)

# Rate limiting for test-send endpoint: max 1 per 60 seconds per user
_LAST_TEST_SEND_TIMESTAMP: Dict[int, float] = {}
TIME_FORMAT_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

VALID_RULES = {
    "low_stock",
    "expiry_risk",
    "payment_verified",
    "count_mismatch",
    "scanner_failure",
    "webhook_failed"
}

@notifications_bp.route("/notifications", methods=["GET"])
def get_notifications():
    """
    List delivery log of notifications with optional filters for rule and status.
    Supports pagination: limit and offset.
    """
    user = get_current_user_context(request)
    rule = request.args.get("rule")
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)

    # Role-based filtering
    user_role = user.get("role", "retailer")
    user_id = user.get("user_id", 1)

    with get_db_session() as session:
        query = session.query(Notification)

        # Non-admins cannot view webhook_failed alerts (admin-only security rule)
        if user_role != "admin":
            query = query.filter(Notification.rule != "webhook_failed")

        if rule and rule in VALID_RULES:
            query = query.filter(Notification.rule == rule)

        if status:
            query = query.filter(Notification.status == status)

        total_count = query.count()
        notifs = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

        results = [
            {
                "id": n.id,
                "rule": n.rule,
                "title": n.title,
                "message": n.message,
                "priority": n.priority,
                "tags": n.tags,
                "event_ref": n.event_ref,
                "dedup_key": n.dedup_key,
                "status": n.status,
                "attempts": n.attempts,
                "last_error": n.last_error,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None
            }
            for n in notifs
        ]

    return jsonify({
        "status": "success",
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "notifications": results
    }), 200

@notifications_bp.route("/notifications/settings", methods=["GET"])
def get_settings():
    """
    Retrieves notification rules, thresholds, and quiet hours configuration.
    """
    user = get_current_user_context(request)
    requested_owner = request.args.get("owner_id")

    if requested_owner and user.get("role") == "admin":
        owner_id = int(requested_owner)
    else:
        owner_id = user.get("user_id", 1)

    with get_db_session() as session:
        repo = NotificationRepository(session)
        settings = repo.get_settings_by_owner(owner_id=owner_id)

        # Fallback to defaults for owner if not yet initialized
        if not settings:
            settings = repo.get_settings_by_owner(owner_id=1)

        results = [
            {
                "id": s.id,
                "rule": s.rule,
                "enabled": bool(s.enabled),
                "threshold": s.threshold,
                "quiet_hours_start": s.quiet_hours_start,
                "quiet_hours_end": s.quiet_hours_end,
                "min_minutes_between": s.min_minutes_between
            }
            for s in settings
        ]

    return jsonify({
        "status": "success",
        "owner_id": owner_id,
        "settings": results
    }), 200

@notifications_bp.route("/notifications/settings", methods=["PUT"])
def update_settings():
    """
    Update notification rules and thresholds.
    Security: Validates input ranges, time format (HH:MM), and role access.
    Only admins can edit global/other user settings; owners edit their own.
    """
    user = get_current_user_context(request)
    payload = request.get_json(silent=True) or {}

    items = payload if isinstance(payload, list) else [payload]
    if not items:
        return jsonify({"error": "No settings provided"}), 400

    target_owner = int(request.args.get("owner_id", user.get("user_id", 1)))
    if target_owner != user.get("user_id") and user.get("role") != "admin":
        return jsonify({"error": "Forbidden: Only admins can configure settings for other accounts"}), 403

    updated_count = 0
    with get_db_session() as session:
        repo = NotificationRepository(session)

        for item in items:
            rule = item.get("rule")
            if not rule or rule not in VALID_RULES:
                return jsonify({"error": f"Invalid rule '{rule}'. Must be one of: {sorted(list(VALID_RULES))}"}), 400

            # Admin-only check for webhook_failed configuration
            if rule == "webhook_failed" and user.get("role") != "admin":
                return jsonify({"error": "Forbidden: Only administrators can modify webhook failure alert settings"}), 403

            enabled = 1 if item.get("enabled", True) else 0

            # Validate threshold
            threshold_val = item.get("threshold")
            if threshold_val is not None:
                try:
                    thresh = float(threshold_val)
                    if thresh < 0 or thresh > 10000:
                        return jsonify({"error": "Threshold must be between 0 and 10000"}), 400
                except (ValueError, TypeError):
                    return jsonify({"error": "Threshold must be a valid number"}), 400
            else:
                thresh = 10.0

            # Validate quiet hours times
            q_start = item.get("quiet_hours_start", "22:00")
            q_end = item.get("quiet_hours_end", "07:00")
            if not TIME_FORMAT_REGEX.match(q_start) or not TIME_FORMAT_REGEX.match(q_end):
                return jsonify({"error": "Quiet hours must be in 24-hour HH:MM format (e.g. '22:00', '07:00')"}), 400

            # Validate min_minutes_between
            min_mins = item.get("min_minutes_between", 60)
            try:
                min_mins = max(1, min(1440, int(min_mins)))
            except (ValueError, TypeError):
                return jsonify({"error": "min_minutes_between must be an integer between 1 and 1440"}), 400

            repo.upsert_setting(
                rule=rule,
                owner_id=target_owner,
                enabled=enabled,
                threshold=thresh,
                quiet_hours_start=q_start,
                quiet_hours_end=q_end,
                min_minutes_between=min_mins
            )
            updated_count += 1

        session.commit()

    return jsonify({
        "status": "success",
        "updated_count": updated_count,
        "message": "Notification settings updated successfully."
    }), 200

@notifications_bp.route("/notifications/test-send", methods=["POST"])
def send_test_notification():
    """
    Test send endpoint. Rate limited to 1 request per 60 seconds per user.
    Enqueues a test notification to verify mobile subscriber delivery.
    """
    user = get_current_user_context(request)
    user_id = user.get("user_id", 1)
    now = time.time()

    # Rate Limit Check: 1 send per 60 seconds
    last_sent = _LAST_TEST_SEND_TIMESTAMP.get(user_id, 0.0)
    if (now - last_sent) < 60.0:
        retry_after = int(60.0 - (now - last_sent))
        return jsonify({
            "error": "Rate limit exceeded. Please wait between test notification sends.",
            "retry_after_seconds": retry_after
        }), 429

    _LAST_TEST_SEND_TIMESTAMP[user_id] = now
    now_str = datetime.datetime.now().strftime("%I:%M %p")

    # Enqueue test alert (priority 3, ignores quiet hours for verification)
    res = enqueue_notification(
        rule="low_stock",
        title="StockSense Push Verification",
        message=f"Real-time alerts active! Mobile notification channel verified at {now_str}.",
        priority=3,
        tags="white_check_mark,bell",
        event_ref=f"test_evt_{uuid.uuid4().hex[:8]}",
        dedup_key=f"test_send_{user_id}_{int(now)}",
        owner_id=user_id,
        ignore_quiet_hours=True
    )

    return jsonify({
        "status": "success",
        "notification_id": res.get("id"),
        "delivery_state": res.get("status"),
        "message": "Test push notification enqueued to background delivery queue."
    }), 200

@notifications_bp.route("/notifications/topic-info", methods=["GET"])
def get_topic_info():
    """
    Provides secure topic connection details for mobile app setup.
    Security non-negotiable: NEVER returns or displays the full topic! Only masked topic (***XXXX).
    """
    base_url = get_ntfy_base_url()
    topic = get_ntfy_topic()
    masked = mask_topic(topic)

    return jsonify({
        "status": "success",
        "base_url": base_url,
        "masked_topic": masked,
        "instructions": [
            "1. Install the ntfy app on iOS (App Store) or Android (Google Play / F-Droid).",
            "2. Open the app and tap the '+' button to subscribe to a topic.",
            f"3. In server settings, use '{base_url}' (or your configured self-hosted instance).",
            "4. Enter your secret environment-configured topic name to begin receiving push alerts."
        ]
    }), 200
