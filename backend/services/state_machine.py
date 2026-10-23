import datetime
from typing import Dict, Any, Optional
from backend.database import get_db_session
from backend.repositories.session_repository import SessionRepository, LEGAL_TRANSITIONS
from backend.models.orm_models import ScanSession, Setting

class SessionState:
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    BASKET = "BASKET"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    RECORDING = "RECORDING"

def get_current_session_info() -> Dict[str, Any]:
    """
    Returns current active session, evaluating server-side timeouts.
    Single source of truth for UI state machine.
    """
    with get_db_session() as session:
        repo = SessionRepository(session)
        scan_session = repo.get_or_create_active_session()

        # Check for server-side timeouts
        now = datetime.datetime.utcnow()
        if scan_session.state == SessionState.PAYMENT_PENDING:
            timeout_setting = session.query(Setting).filter_by(key="payment_timeout_minutes").first()
            timeout_mins = int(timeout_setting.value) if timeout_setting else 5
            # Get latest transition to PAYMENT_PENDING
            latest_trans = scan_session.transitions[-1] if scan_session.transitions else None
            trans_time = latest_trans.at if latest_trans else scan_session.started_at
            if (now - trans_time).total_seconds() > (timeout_mins * 60):
                repo.transition_state(scan_session.id, SessionState.BASKET, reason="Payment window expired")
                scan_session = repo.get_by_id(scan_session.id)

        elif scan_session.state == SessionState.RECORDING:
            timeout_setting = session.query(Setting).filter_by(key="recording_timeout_minutes").first()
            timeout_mins = int(timeout_setting.value) if timeout_setting else 10
            latest_trans = scan_session.transitions[-1] if scan_session.transitions else None
            trans_time = latest_trans.at if latest_trans else scan_session.started_at
            if (now - trans_time).total_seconds() > (timeout_mins * 60):
                repo.transition_state(scan_session.id, SessionState.IDLE, reason="Recording session inactivity timeout")
                scan_session = repo.get_by_id(scan_session.id)

        allowed_next = sorted(list(LEGAL_TRANSITIONS.get(scan_session.state, set())))

        return {
            "session_id": scan_session.id,
            "session_uuid": scan_session.session_uuid,
            "state": scan_session.state,
            "started_at": scan_session.started_at.isoformat() if scan_session.started_at else None,
            "ended_at": scan_session.ended_at.isoformat() if scan_session.ended_at else None,
            "allowed_transitions": allowed_next,
            "transitions_count": len(scan_session.transitions)
        }

def transition_checkout_session(
    to_state: str,
    reason: Optional[str] = None,
    session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes a formal state transition. Throws ValueError if illegal.
    """
    with get_db_session() as session:
        repo = SessionRepository(session)
        if session_id:
            scan_session = repo.get_by_id(session_id)
        else:
            scan_session = repo.get_or_create_active_session()

        if not scan_session:
            raise ValueError("No active session found")

        updated = repo.transition_state(scan_session.id, to_state, reason=reason)
        allowed_next = sorted(list(LEGAL_TRANSITIONS.get(updated.state, set())))

        return {
            "session_id": updated.id,
            "session_uuid": updated.session_uuid,
            "state": updated.state,
            "allowed_transitions": allowed_next,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
