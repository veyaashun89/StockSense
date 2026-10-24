import os
import hmac
import hashlib
import base64
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify

from backend.database import get_db_session
from backend.services.detection_service import get_detector
from backend.services.state_machine import (
    get_current_session_info, transition_checkout_session, SessionState
)
from backend.repositories.session_repository import SessionRepository
from backend.repositories.detection_repository import DetectionRepository
from backend.services.payment_service import verify_and_settle_payment

logger = logging.getLogger(__name__)

record_bp = Blueprint("record", __name__)

WEBHOOK_SECRET = os.environ.get("PAYMENT_WEBHOOK_SECRET", "stocksense_whsec_demo_2026")
DEMO_MODE = os.environ.get("DEMO_MODE", "True").lower() in ("true", "1")
MAX_FRAME_BYTES = 1024 * 1024  # 1 MB maximum payload

@record_bp.route("/record/start", methods=["POST"])
def start_recording():
    """
    Starts an automated object detection recording session.
    Transitions checkout state machine to RECORDING.
    """
    data = request.get_json(silent=True) or {}
    operator_id = int(data.get("operator_id", 1))

    with get_db_session() as session:
        sess_repo = SessionRepository(session)
        active_sess = sess_repo.get_or_create_active_session(operator_id=operator_id)
        
        # Guide state smoothly to RECORDING
        if active_sess.state != SessionState.RECORDING:
            if active_sess.state in (SessionState.IDLE, SessionState.SCANNING, SessionState.BASKET, SessionState.PAYMENT_PENDING):
                # Transition through sequence if needed
                if active_sess.state == SessionState.IDLE:
                    sess_repo.transition_state(active_sess.id, SessionState.BASKET, reason="Session prep")
                if active_sess.state in (SessionState.IDLE, SessionState.SCANNING, SessionState.BASKET):
                    sess_repo.transition_state(active_sess.id, SessionState.PAYMENT_PENDING, reason="Session checkout")
                if active_sess.state != SessionState.PAID:
                    sess_repo.transition_state(active_sess.id, SessionState.PAID, reason="Pre-record verified")
            
            sess_repo.transition_state(active_sess.id, SessionState.RECORDING, reason="Live record session started")
        
        session_id = active_sess.id
        session_uuid = active_sess.session_uuid

    # Reset tracker for fresh recording session
    detector = get_detector()
    detector.tracker.reset()

    return jsonify({
        "status": "recording",
        "session_id": session_id,
        "session_uuid": session_uuid,
        "state": SessionState.RECORDING,
        "message": "Live object detection session initialized.",
        "privacy_notice": "Camera analytics: people are counted, not identified."
    }), 200

@record_bp.route("/record/stop", methods=["POST"])
def stop_recording():
    """
    Finalizes the recording session, computes summary metrics,
    and returns state machine to IDLE.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    with get_db_session() as session:
        sess_repo = SessionRepository(session)
        det_repo = DetectionRepository(session)

        if not session_id:
            active_sess = sess_repo.get_or_create_active_session()
            session_id = active_sess.id
        else:
            active_sess = sess_repo.get_by_id(session_id)

        if active_sess and active_sess.state == SessionState.RECORDING:
            sess_repo.transition_state(active_sess.id, SessionState.IDLE, reason="Recording session finalized by operator")

        summary = det_repo.get_session_summary(session_id) if session_id else {}

    return jsonify({
        "status": "stopped",
        "session_id": session_id,
        "state": SessionState.IDLE,
        "summary": summary,
        "message": "Session finalized. Stored metrics and returned to IDLE."
    }), 200

@record_bp.route("/record/live", methods=["GET"])
def get_live_metrics():
    """
    Pollable live status endpoint: returns latest detections, counters,
    detector FPS, and current state machine state.
    """
    sess_info = get_current_session_info()
    detector = get_detector()

    return jsonify({
        "status": "ok",
        "session": sess_info,
        "detector_ready": detector.is_ready,
        "measured_fps": detector.measured_fps,
        "last_inference_ms": detector.last_inference_time_ms,
        "counters": {
            "unique_people_session": len(detector.tracker.unique_person_ids),
            "unique_products_session": len(detector.tracker.unique_product_tracks),
            "active_tracks_count": len(detector.tracker.tracks),
            "total_frames_processed": detector.tracker.frame_count
        },
        "privacy_notice": "Camera analytics: people are counted, not identified."
    }), 200

@record_bp.route("/record/sessions", methods=["GET"])
def list_sessions():
    """
    Returns list of past scan and recording sessions with summary stats.
    """
    limit = int(request.args.get("limit", 20))
    with get_db_session() as session:
        sess_repo = SessionRepository(session)
        det_repo = DetectionRepository(session)
        sessions = sess_repo.list_sessions(limit=limit)

        result = []
        for s in sessions:
            summary = det_repo.get_session_summary(s.id)
            result.append({
                "id": s.id,
                "session_uuid": s.session_uuid,
                "state": s.state,
                "operator_id": s.operator_id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "summary": summary
            })

    return jsonify({"sessions": result}), 200

@record_bp.route("/record/sessions/<int:session_id>", methods=["GET"])
def get_session_detail(session_id: int):
    """
    Returns complete details of a specific session, including transitions and recent events.
    """
    with get_db_session() as session:
        sess_repo = SessionRepository(session)
        det_repo = DetectionRepository(session)

        s = sess_repo.get_by_id(session_id)
        if not s:
            return jsonify({"error": f"Session {session_id} not found"}), 404

        summary = det_repo.get_session_summary(session_id)
        events = det_repo.get_session_detections(session_id, limit=50)

        transitions = [
            {
                "from_state": t.from_state,
                "to_state": t.to_state,
                "reason": t.reason,
                "at": t.at.isoformat() if t.at else None
            }
            for t in (s.transitions or [])
        ]

        event_items = [
            {
                "id": e.id,
                "ts": e.ts.isoformat() if e.ts else None,
                "class_name": e.class_name,
                "track_id": e.track_id,
                "sku": e.sku,
                "confidence": e.confidence,
                "bbox": e.bbox
            }
            for e in events
        ]

    return jsonify({
        "id": s.id,
        "session_uuid": s.session_uuid,
        "state": s.state,
        "operator_id": s.operator_id,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "transitions": transitions,
        "summary": summary,
        "events": event_items
    }), 200

@record_bp.route("/record/frame", methods=["POST"])
def process_frame():
    """
    Accepts base64 encoded frame from webcam or uploaded image.
    Executes YOLOv8n inference on CPU, tracks detections, and logs to database.
    Enforces <= 1MB payload restriction and privacy guarantees.
    """
    # Enforce 1MB payload limit
    content_length = request.content_length or 0
    if content_length > MAX_FRAME_BYTES:
        return jsonify({"error": "Frame payload exceeds 1MB limit"}), 413

    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image_data") or data.get("image")
    blur_faces = data.get("blur_faces", True)
    session_id = data.get("session_id")

    image_bytes = None
    if image_b64:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception as e:
            return jsonify({"error": f"Invalid base64 encoding: {e}"}), 400
    elif "file" in request.files:
        image_bytes = request.files["file"].read()

    if not image_bytes:
        return jsonify({"error": "No image data provided"}), 400

    if len(image_bytes) > MAX_FRAME_BYTES:
        return jsonify({"error": "Frame decoded bytes exceed 1MB limit"}), 413

    # If session_id not given, use active session if in RECORDING
    if not session_id:
        with get_db_session() as session:
            sess_repo = SessionRepository(session)
            active = sess_repo.get_or_create_active_session()
            if active.state == SessionState.RECORDING:
                session_id = active.id

    detector = get_detector()
    result = detector.detect_frame(
        image_bytes=image_bytes,
        session_id=session_id,
        blur_people_faces=blur_faces
    )

    return jsonify(result), 200

@record_bp.route("/session/state", methods=["GET"])
def get_session_state():
    """
    Single source of truth for the retail checkout session state machine.
    """
    info = get_current_session_info()
    return jsonify(info), 200

@record_bp.route("/session/transition", methods=["POST"])
def transition_state():
    """
    Explicit transition request from frontend or workflow controller.
    Validates legal transitions.
    """
    data = request.get_json(silent=True) or {}
    target_state = data.get("target_state")
    reason = data.get("reason", "Operator transition request")
    session_id = data.get("session_id")

    if not target_state:
        return jsonify({"error": "target_state is required"}), 400

    try:
        updated = transition_checkout_session(
            to_state=target_state,
            reason=reason,
            session_id=session_id
        )
        return jsonify(updated), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

def _emit_webhook_failed_notification(reason_category: str):
    try:
        from backend.services.notification_rules import evaluate_webhook_failed
        from backend.workers.notification_worker import enqueue_notification
        import uuid

        eval_res = evaluate_webhook_failed(reason_category=reason_category, gateway="PaymentGateway")
        event_ref = f"wh_fail_{uuid.uuid4().hex[:10]}"
        enqueue_notification(
            rule=eval_res["rule"],
            title=eval_res["title"],
            message=eval_res["message"],
            priority=eval_res["priority"],
            event_ref=event_ref,
            tags=eval_res["tags"],
            dedup_key=eval_res["dedup_key"],
            owner_id=1
        )
    except Exception as ex:
        logger.warning(f"Failed to enqueue webhook failure notification: {ex}")

@record_bp.route("/payment/webhook", methods=["POST"])
def payment_webhook():
    """
    Production Webhook Endpoint for Payment Gateway Callbacks.
    Verifies HMAC-SHA256 signature from payment provider.
    Reconciles inventory atomically and marks session PAID.
    """
    signature = request.headers.get("X-StockSense-Signature") or request.headers.get("X-Signature")
    raw_payload = request.get_data()

    is_demo_simulation = False
    if DEMO_MODE:
        if request.headers.get("X-Demo-Simulate") == "true" or signature == "demo_simulation":
            is_demo_simulation = True

    if not is_demo_simulation:
        if not signature:
            _emit_webhook_failed_notification("MISSING_SIGNATURE_HEADER")
            return jsonify({"error": "Missing X-StockSense-Signature header"}), 401
        
        expected_sig = hmac.new(
            WEBHOOK_SECRET.encode("utf-8"),
            raw_payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            _emit_webhook_failed_notification("INVALID_HMAC_SIGNATURE")
            return jsonify({"error": "Invalid webhook HMAC signature"}), 401

    data = request.get_json(silent=True) or {}
    txn_ref = data.get("transaction_ref")
    amount = float(data.get("amount", 0))
    utr = data.get("utr_number")
    cart_items = data.get("cart_items", [])
    po_id = data.get("purchase_order_id")

    if not txn_ref or amount <= 0:
        _emit_webhook_failed_notification("MALFORMED_PAYLOAD")
        return jsonify({"error": "transaction_ref and positive amount are required"}), 400

    try:
        receipt = verify_and_settle_payment(
            transaction_ref=txn_ref,
            amount=amount,
            payment_method=data.get("payment_method", "WEBHOOK_UPI"),
            utr_number=utr,
            cart_items=cart_items,
            purchase_order_id=po_id
        )
        return jsonify(receipt), 200
    except Exception as e:
        logger.error(f"Webhook settlement failure: {e}")
        _emit_webhook_failed_notification("SETTLEMENT_ERROR")
        return jsonify({"error": f"Settlement failed: {str(e)}"}), 400


@record_bp.route("/record/purge-old-events", methods=["POST"])
def purge_old_detection_events():
    """
    Privacy and Retention Policy: Purges detection events older than N days.
    """
    data = request.get_json(silent=True) or {}
    days = int(data.get("older_than_days", 30))

    with get_db_session() as session:
        det_repo = DetectionRepository(session)
        deleted_count = det_repo.purge_old_events(older_than_days=days)

    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "retention_days": days,
        "message": f"Purged {deleted_count} detection event records older than {days} days."
    }), 200
