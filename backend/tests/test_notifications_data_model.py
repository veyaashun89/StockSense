import pytest
import datetime
from backend.app import create_app
from backend.database import get_db_session, init_db
from backend.repositories.notification_repository import NotificationRepository
from backend.models.orm_models import Notification, NotificationSetting

@pytest.fixture
def app_context():
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        yield app

def test_notification_tables_created_and_seeded(app_context):
    with get_db_session() as session:
        repo = NotificationRepository(session)
        settings = repo.get_settings(owner_id=1)
        assert len(settings) >= 6
        rules = {s.rule for s in settings}
        assert "low_stock" in rules
        assert "expiry_risk" in rules
        assert "payment_verified" in rules
        assert "count_mismatch" in rules
        assert "scanner_failure" in rules
        assert "webhook_failed" in rules

def test_notification_creation_and_deduplication(app_context):
    import uuid
    notif_id = None
    test_key = f"dedup_low_stock_milk_store1_{uuid.uuid4().hex[:8]}"
    with get_db_session() as session:
        repo = NotificationRepository(session)
        notif = repo.create(
            rule="low_stock",
            title="Low Stock: Milk",
            message="Only 2 units remaining at Store #1",
            priority=4,
            tags="warning,milk",
            event_ref="evt_stock_001",
            dedup_key=test_key,
            status="pending"
        )
        assert notif.id is not None
        assert notif.rule == "low_stock"
        assert notif.event_ref == "evt_stock_001"
        assert notif.status == "pending"
        notif_id = notif.id

        # Lookup by dedup_key
        found = repo.get_by_dedup_key(test_key)
        assert found is not None
        assert found.id == notif_id

        # Update delivery status
        repo.update_delivery_status(notif_id, status="sent", sent_at=datetime.datetime.utcnow(), attempts=1)

    with get_db_session() as session:
        repo = NotificationRepository(session)
        updated = repo.get_by_id(notif_id)
        assert updated.status == "sent"
        assert updated.attempts == 1
        assert updated.sent_at is not None
