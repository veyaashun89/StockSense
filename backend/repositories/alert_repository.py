import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from backend.models.orm_models import Alert
from backend.repositories.base_repository import BaseRepository

class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: Session):
        super().__init__(Alert, session)

    def get_by_dedup_key(self, dedup_key: str) -> Optional[Alert]:
        stmt = select(Alert).where(Alert.dedup_key == dedup_key)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_or_dedup_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        dedup_key: str,
        severity: str = "MEDIUM",
        product_id: Optional[int] = None,
        sku: Optional[str] = None,
        explanation: Optional[str] = None,
        payload: Optional[str] = None
    ) -> Tuple_Alert_Bool := tuple:  # type: ignore
        existing = self.get_by_dedup_key(dedup_key)
        if existing:
            # If already open, do not duplicate
            if existing.status == "OPEN":
                return existing, False
            else:
                # Reopen if previously resolved
                existing.status = "OPEN"
                existing.message = message
                existing.created_at = datetime.datetime.utcnow()
                existing.resolved_at = None
                self.session.flush()
                return existing, True

        alert = Alert(
            type=alert_type,
            title=title,
            message=message,
            dedup_key=dedup_key,
            severity=severity,
            product_id=product_id,
            sku=sku,
            explanation=explanation,
            payload=payload,
            status="OPEN"
        )
        self.session.add(alert)
        self.session.flush()
        return alert, True

    def resolve_alert(self, alert_id: int) -> Optional[Alert]:
        alert = self.get_by_id(alert_id)
        if alert and alert.status != "RESOLVED":
            alert.status = "RESOLVED"
            alert.resolved_at = datetime.datetime.utcnow()
            self.session.flush()
        return alert

    def get_open_alerts(self, shop_id: int = 1) -> List[Alert]:
        stmt = select(Alert).where(Alert.status == "OPEN", Alert.shop_id == shop_id)
        return list(self.session.execute(stmt).scalars().all())
