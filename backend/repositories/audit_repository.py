import json
import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.models.orm_models import AuditLog
from backend.repositories.base_repository import BaseRepository

class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: Session):
        super().__init__(AuditLog, session)

    def log(
        self,
        action: str,
        entity: str,
        entity_id: Optional[str] = None,
        actor_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        audit = AuditLog(
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            actor_id=actor_id,
            payload_json=json.dumps(payload) if payload is not None else None,
            at=datetime.datetime.utcnow()
        )
        self.session.add(audit)
        self.session.flush()
        return audit
