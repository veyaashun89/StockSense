import pytest
import time
import uuid
from unittest.mock import patch, MagicMock

from backend.database import get_db_session
from backend.models.orm_models import Product, Location, Notification
from backend.repositories.inventory_repository import InventoryRepository
from backend.repositories.location_repository import LocationRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.services.payment_service import verify_and_settle_payment
from backend.services.alert_service import evaluate_and_generate_alerts
from backend.routes.scanner import record_scanner_failure, reset_scanner_failures
from backend.routes.record import _emit_webhook_failed_notification

@pytest.fixture(autouse=True)
def setup_test_data():
    reset_scanner_failures()
    with get_db_session() as session:
        sku = f"TEST-HOOK-{uuid.uuid4().hex[:6]}"
        prod = Product(
            sku=sku,
            name="Organic Almond Milk",
            category="Beverages",
            selling_price=120.00,
            unit_cost=90.00,
            current_stock=10
        )
        session.add(prod)
        session.commit()
        session.refresh(prod)
        prod_id = prod.id

    loc_dict = LocationRepository.create_location(
        name=f"Store-Hook-{uuid.uuid4().hex[:4]}",
        location_type="shelf"
    )

    yield prod_id, loc_dict["id"], loc_dict["name"], sku

def test_payment_verified_commits_when_ntfy_down(setup_test_data):
    """
    Business requirement: When payment is settled, transaction commits cleanly
    and receipt is generated even if ntfy is failing with 500 errors.
    Non-negotiable: No customer names, phone numbers, UPI IDs, or UTR numbers in notification.
    """
    prod_id, loc_id, loc_name, sku = setup_test_data
    txn_ref = f"TXN-{uuid.uuid4().hex[:8]}"
    test_utr = f"UTR-{uuid.uuid4().hex[:10].upper()}"

    # Mock requests.post returning 500 server error
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Server Error"

    with patch("requests.post", return_value=mock_resp):
        receipt = verify_and_settle_payment(
            transaction_ref=txn_ref,
            amount=240.0,
            payment_method="UPI_INTENT",
            utr_number=test_utr,
            cart_items=[{"product_id": prod_id, "quantity": 2, "price": 120.0}]
        )

        assert receipt["status"] == "SUCCESS"
        assert receipt["transaction_ref"] == txn_ref

    # Verify notification was recorded in DB
    with get_db_session() as session:
        notifs = session.query(Notification).filter_by(event_ref=txn_ref).all()
        assert len(notifs) >= 1
        notif = notifs[0]
        assert notif.rule == "payment_verified"
        assert notif.priority == 2
        # Verify privacy: NO phone number, NO UTR, NO customer identifiers
        assert "+91" not in notif.message
        assert test_utr not in notif.message
        assert "₹240.00" in notif.message or "240" in notif.message

def test_low_stock_commits_when_ntfy_down(setup_test_data):
    """
    Business requirement: Stock deduction updates inventory even if ntfy fails.
    """
    prod_id, loc_id, loc_name, sku = setup_test_data
    with get_db_session() as session:
        inv_repo = InventoryRepository(session)
        inv = inv_repo.get_or_create(product_id=prod_id, owner_id=1, initial_stock=6)
        inv.reorder_level = 5
        session.commit()

        # Mock ntfy returning connection error
        with patch("requests.post", side_effect=Exception("Connection refused")):
            # Deduct down below reorder level (reorder_level is 5, deduction leaves 2)
            new_bal, movement = inv_repo.deduct_stock(
                product_id=prod_id,
                owner_id=1,
                qty=4,
                reason="POS Sale"
            )
            session.commit()

            assert new_bal == 2
            assert movement.delta == -4

        # Check notification logged in DB
        notif = session.query(Notification).filter(
            Notification.rule == "low_stock",
            Notification.message.like(f"%{sku}%")
        ).first()
        assert notif is not None
        assert notif.priority == 3
        assert "left at" in notif.message

def test_expiry_risk_commits_when_ntfy_down(setup_test_data):
    """
    Expiry evaluation alerts operator without interrupting alerting loop.
    """
    prod_id, loc_id, loc_name, sku = setup_test_data
    with patch("requests.post", side_effect=Exception("Timeout")):
        alerts = evaluate_and_generate_alerts(shop_id=1)
        assert isinstance(alerts, dict)

def test_count_mismatch_commits_when_ntfy_down(setup_test_data):
    """
    Location box count reconciliation writes audit record and emits mismatch notification.
    """
    prod_id, loc_id, loc_name, sku = setup_test_data
    LocationRepository.set_location_stock(location_id=loc_id, sku=sku, expected_qty=20)

    with patch("requests.post", side_effect=Exception("Network error")):
        res = LocationRepository.reconcile_box_counts(
            location_id=loc_id,
            scanned_counts={sku: 18}
        )
        assert res["mismatch_count"] == 1
        assert res["reconciled_items"][0]["difference"] == -2

    with get_db_session() as session:
        notif = session.query(Notification).filter(
            Notification.rule == "count_mismatch",
            Notification.message.like(f"%{sku}%")
        ).first()
        assert notif is not None
        assert notif.priority == 4
        assert "-2" in notif.message
        assert loc_name in notif.message

def test_scanner_failure_threshold_trigger():
    """
    Scanner failure requires 3 failures in 10 minutes before notifying.
    """
    reset_scanner_failures()
    # 1st failure -> no notification
    c1 = record_scanner_failure(reason="Low light blur", terminal_id="Reg-Test-1")
    assert c1 == 1

    # 2nd failure -> no notification
    c2 = record_scanner_failure(reason="Low light blur", terminal_id="Reg-Test-1")
    assert c2 == 2

    # 3rd failure -> notification emitted!
    c3 = record_scanner_failure(reason="Low light blur", terminal_id="Reg-Test-1")
    assert c3 == 3

    with get_db_session() as session:
        notif = session.query(Notification).filter(
            Notification.rule == "scanner_failure",
            Notification.message.like("%Reg-Test-1%")
        ).first()
        assert notif is not None
        assert notif.priority == 3
        assert "3 consecutive recognition failures" in notif.message

def test_webhook_failed_emitted_with_sanitized_reason():
    """
    Webhook failure notification must have priority 5 and no raw payload.
    """
    _emit_webhook_failed_notification("INVALID_HMAC_SIGNATURE")

    with get_db_session() as session:
        notif = session.query(Notification).filter(
            Notification.rule == "webhook_failed",
            Notification.message.like("%INVALID_HMAC_SIGNATURE%")
        ).first()
        assert notif is not None
        assert notif.priority == 5
        assert "INVALID_HMAC_SIGNATURE" in notif.message
        assert "Security Alert" in notif.message
