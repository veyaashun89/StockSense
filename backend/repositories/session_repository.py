import uuid
import datetime
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from backend.models.orm_models import ScanSession, StateTransition
from backend.repositories.base_repository import BaseRepository

LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    "IDLE": {"SCANNING", "BASKET"},
    "SCANNING": {"BASKET", "IDLE"},
    "BASKET": {"PAYMENT_PENDING", "SCANNING", "IDLE"},
    "PAYMENT_PENDING": {"PAID", "BASKET", "IDLE"},
    "PAID": {"RECORDING", "IDLE"},
    "RECORDING": {"IDLE"}
}

class SessionRepository(BaseRepository[ScanSession]):
    def __init__(self, session: Session):
        super().__init__(ScanSession, session)

    def get_by_uuid(self, session_uuid: str) -> Optional[ScanSession]:
        stmt = select(ScanSession).where(ScanSession.session_uuid == session_uuid)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_latest_session(self) -> Optional[ScanSession]:
        stmt = select(ScanSession).order_by(desc(ScanSession.started_at)).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create_active_session(self, operator_id: int = 1) -> ScanSession:
        latest = self.get_latest_session()
        if latest and latest.state != "IDLE":
            return latest

        new_session = ScanSession(
            session_uuid=f"sess_{uuid.uuid4().hex[:12]}",
            state="IDLE",
            operator_id=operator_id,
            started_at=datetime.datetime.utcnow()
        )
        self.session.add(new_session)
        self.session.flush()

        initial_transition = StateTransition(
            session_id=new_session.id,
            from_state="NONE",
            to_state="IDLE",
            reason="Session initialized",
            at=datetime.datetime.utcnow()
        )
        self.session.add(initial_transition)
        self.session.flush()
        return new_session

    def transition_state(
        self,
        session_id: int,
        to_state: str,
        reason: Optional[str] = None
    ) -> ScanSession:
        scan_session = self.get_by_id(session_id)
        if not scan_session:
            raise ValueError(f"ScanSession with ID {session_id} not found")

        current_state = scan_session.state
        allowed = LEGAL_TRANSITIONS.get(current_state, set())

        if to_state not in allowed and to_state != current_state:
            raise ValueError(
                f"Illegal state transition from '{current_state}' to '{to_state}'. Allowed transitions: {sorted(list(allowed))}"
            )

        if to_state != current_state:
            scan_session.state = to_state
            if to_state == "IDLE":
                scan_session.ended_at = datetime.datetime.utcnow()

            transition = StateTransition(
                session_id=scan_session.id,
                from_state=current_state,
                to_state=to_state,
                reason=reason or f"Transition to {to_state}",
                at=datetime.datetime.utcnow()
            )
            self.session.add(transition)
            self.session.flush()

        return scan_session

    def list_sessions(self, limit: int = 50) -> List[ScanSession]:
        stmt = select(ScanSession).order_by(desc(ScanSession.started_at)).limit(limit)
        return list(self.session.execute(stmt).scalars().all())
