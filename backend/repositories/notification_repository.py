import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc

from backend.models.orm_models import Notification, NotificationSetting
from backend.repositories.base_repository import BaseRepository

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: Session):
        super().__init__(Notification, session)

    def create(
        self,
        rule: str,
        title: str,
        message: str,
        priority: int,
        tags: Optional[str],
        event_ref: str,
        dedup_key: str,
        status: str = "pending"
    ) -> Notification:
        notif = Notification(
            rule=rule,
            title=title,
            message=message,
            priority=priority,
            tags=tags,
            event_ref=event_ref,
            dedup_key=dedup_key,
            status=status,
            attempts=0,
            created_at=datetime.datetime.utcnow()
        )
        self.session.add(notif)
        self.session.flush()
        return notif

    def get_by_dedup_key(self, dedup_key: str) -> Optional[Notification]:
        stmt = select(Notification).where(Notification.dedup_key == dedup_key)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_notifications(
        self,
        rule: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        stmt = select(Notification).order_by(desc(Notification.created_at))
        if rule and rule != "all":
            stmt = stmt.where(Notification.rule == rule)
        if status and status != "all":
            stmt = stmt.where(Notification.status == status)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def count_notifications(
        self,
        rule: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        stmt = select(func.count(Notification.id))
        if rule and rule != "all":
            stmt = stmt.where(Notification.rule == rule)
        if status and status != "all":
            stmt = stmt.where(Notification.status == status)
        return self.session.execute(stmt).scalar() or 0

    def update_delivery_status(
        self,
        notification_id: int,
        status: str,
        last_error: Optional[str] = None,
        sent_at: Optional[datetime.datetime] = None,
        attempts: Optional[int] = None
    ) -> Optional[Notification]:
        notif = self.get_by_id(notification_id)
        if not notif:
            return None
        notif.status = status
        if last_error is not None:
            notif.last_error = last_error
        if sent_at is not None:
            notif.sent_at = sent_at
        if attempts is not None:
            notif.attempts = attempts
        else:
            notif.attempts = (notif.attempts or 0) + 1
        self.session.flush()
        return notif

    def get_pending(self, limit: int = 20) -> List[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.status == "pending")
            .order_by(desc(Notification.priority), Notification.created_at)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_sent_in_last_hour(self, window_hours: int = 1) -> int:
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=window_hours)
        stmt = select(func.count(Notification.id)).where(
            Notification.status == "sent",
            Notification.created_at >= since
        )
        return self.session.execute(stmt).scalar() or 0

    # -------------------------------------------------------------
    # Notification Settings
    # -------------------------------------------------------------
    def get_settings(self, owner_id: int = 1) -> List[NotificationSetting]:
        stmt = select(NotificationSetting).where(NotificationSetting.owner_id == owner_id)
        return list(self.session.execute(stmt).scalars().all())

    get_settings_by_owner = get_settings

    def get_setting_by_rule(self, rule: str, owner_id: int = 1) -> Optional[NotificationSetting]:
        stmt = select(NotificationSetting).where(
            NotificationSetting.owner_id == owner_id,
            NotificationSetting.rule == rule
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_setting(
        self,
        rule: str,
        enabled: int,
        threshold: float,
        quiet_hours_start: str = "22:00",
        quiet_hours_end: str = "07:00",
        min_minutes_between: int = 60,
        owner_id: int = 1
    ) -> NotificationSetting:
        setting = self.get_setting_by_rule(rule, owner_id=owner_id)
        if not setting:
            setting = NotificationSetting(
                owner_id=owner_id,
                rule=rule,
                enabled=enabled,
                threshold=threshold,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                min_minutes_between=min_minutes_between
            )
            self.session.add(setting)
        else:
            setting.enabled = enabled
            setting.threshold = threshold
            setting.quiet_hours_start = quiet_hours_start
            setting.quiet_hours_end = quiet_hours_end
            setting.min_minutes_between = min_minutes_between
        self.session.flush()
        return setting
