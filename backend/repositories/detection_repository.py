import json
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, distinct, desc
from backend.models.orm_models import DetectionEvent
from backend.repositories.base_repository import BaseRepository

class DetectionRepository(BaseRepository[DetectionEvent]):
    def __init__(self, session: Session):
        super().__init__(DetectionEvent, session)

    def log_detection(
        self,
        session_id: int,
        class_name: str,
        track_id: int,
        confidence: float,
        bbox: List[float],
        sku: Optional[str] = None
    ) -> DetectionEvent:
        event = DetectionEvent(
            session_id=session_id,
            class_name=class_name,
            track_id=track_id,
            sku=sku,
            confidence=round(confidence, 4),
            bbox_json=json.dumps(bbox),
            ts=datetime.datetime.utcnow()
        )
        self.session.add(event)
        self.session.flush()
        return event

    def get_session_detections(self, session_id: int, limit: int = 100) -> List[DetectionEvent]:
        stmt = (
            select(DetectionEvent)
            .where(DetectionEvent.session_id == session_id)
            .order_by(desc(DetectionEvent.ts))
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_session_summary(self, session_id: int) -> Dict[str, Any]:
        # Count distinct people tracks
        stmt_people = (
            select(func.count(distinct(DetectionEvent.track_id)))
            .where(DetectionEvent.session_id == session_id, DetectionEvent.class_name == "person")
        )
        unique_people = self.session.execute(stmt_people).scalar() or 0

        # Total products detected
        stmt_products = (
            select(func.count(DetectionEvent.id))
            .where(DetectionEvent.session_id == session_id, DetectionEvent.class_name == "product")
        )
        total_products = self.session.execute(stmt_products).scalar() or 0

        # Distinct matched SKUs
        stmt_skus = (
            select(DetectionEvent.sku)
            .distinct()
            .where(
                DetectionEvent.session_id == session_id,
                DetectionEvent.class_name == "product",
                DetectionEvent.sku.isnot(None)
            )
        )
        matched_skus = [s for (s,) in self.session.execute(stmt_skus).all() if s]

        # Total events
        stmt_total = (
            select(func.count(DetectionEvent.id))
            .where(DetectionEvent.session_id == session_id)
        )
        total_events = self.session.execute(stmt_total).scalar() or 0

        return {
            "session_id": session_id,
            "unique_people_count": unique_people,
            "total_products_detected": total_products,
            "matched_skus": matched_skus,
            "matched_skus_count": len(matched_skus),
            "unmatched_items_count": max(0, total_products - len(matched_skus)),
            "total_events": total_events
        }

    def purge_old_events(self, older_than_days: int = 30) -> int:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=older_than_days)
        deleted = (
            self.session.query(DetectionEvent)
            .filter(DetectionEvent.ts < cutoff)
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return deleted
