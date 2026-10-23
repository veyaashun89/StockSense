import os
import tempfile
import pytest
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.models.orm_models import (
    Base, Product, Inventory, InventoryMovement, Sale, SaleItem, Payment,
    ScanSession, StateTransition, AuditLog, User, Shop
)
from backend.utils.money import rupees_to_paise, paise_to_rupees, calculate_gst_paise
from backend.repositories.inventory_repository import InventoryRepository
from backend.repositories.session_repository import SessionRepository, LEGAL_TRANSITIONS
from backend.services.state_machine import SessionState
from backend.services.detection_service import IoUTracker
from backend.services.payment_service import verify_and_settle_payment

@pytest.fixture
def test_db_session():
    """
    Creates an isolated temporary SQLite database for each test to guarantee
    zero contamination of the production database.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    engine = create_engine(
        f"sqlite:///{temp_db_path}",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # Seed baseline shop & user & test product
    shop = Shop(id=1, name="Test Retail Shop")
    session.add(shop)
    session.flush()

    user = User(id=1, email="retailer@stocksense.test", password_hash="dummy", role="retailer", shop_id=1)
    session.add(user)
    session.flush()

    product = Product(
        id=101,
        sku="SKU-TEST-MILK",
        name="Organic Test Milk 1L",
        category="Dairy & Bakery",
        current_stock=10,
        unit_cost=30.0,
        selling_price=45.0,
        retail_price_paise=4500,
        unit_cost_paise=3000,
        gst_rate=5.0,
        is_active=1
    )
    session.add(product)
    session.flush()

    # Initial inventory
    inv = Inventory(product_id=product.id, owner_id=user.id, on_hand=10, reorder_level=5)
    session.add(inv)
    session.commit()

    yield session, engine

    session.close()
    engine.dispose()
    try:
        os.remove(temp_db_path)
    except Exception:
        pass


def test_money_math_integer_paise():
    """
    Validates decimal-safe monetary arithmetic:
    Paise conversions and GST computations without float precision artifacts.
    """
    assert rupees_to_paise(108.50) == 10850
    assert rupees_to_paise(0.0) == 0
    assert rupees_to_paise(45.99) == 4599

    assert paise_to_rupees(10850) == 108.50
    assert paise_to_rupees(4599) == 45.99

    # GST on ₹100.00 at 18% -> ₹18.00 (1800 paise)
    assert calculate_gst_paise(10000, 18.0) == 1800
    # GST on ₹45.00 at 5% -> ₹2.25 (225 paise)
    assert calculate_gst_paise(4500, 5.0) == 225

    # Float drift test: adding 0.1 rupee 100 times in paise equals exactly 1000 paise (₹10.00)
    total_paise = sum(rupees_to_paise(0.10) for _ in range(100))
    assert total_paise == 1000
    assert paise_to_rupees(total_paise) == 10.00


def test_session_state_machine_transitions(test_db_session):
    """
    Validates state machine transitions:
    IDLE -> SCANNING -> BASKET -> PAYMENT_PENDING -> PAID -> RECORDING -> IDLE
    Rejects illegal transitions with ValueError.
    """
    session, _ = test_db_session
    repo = SessionRepository(session)

    scan_sess = repo.get_or_create_active_session()
    assert scan_sess.state == SessionState.IDLE

    # Legal sequence
    repo.transition_state(scan_sess.id, SessionState.SCANNING, reason="Barcode scanner opened")
    assert scan_sess.state == SessionState.SCANNING

    repo.transition_state(scan_sess.id, SessionState.BASKET, reason="Items added to basket")
    assert scan_sess.state == SessionState.BASKET

    repo.transition_state(scan_sess.id, SessionState.PAYMENT_PENDING, reason="UPI QR displayed")
    assert scan_sess.state == SessionState.PAYMENT_PENDING

    repo.transition_state(scan_sess.id, SessionState.PAID, reason="Customer UTR settled")
    assert scan_sess.state == SessionState.PAID

    repo.transition_state(scan_sess.id, SessionState.RECORDING, reason="Auto-navigated to Live Record")
    assert scan_sess.state == SessionState.RECORDING

    repo.transition_state(scan_sess.id, SessionState.IDLE, reason="Session ended")
    assert scan_sess.state == SessionState.IDLE

    # Illegal transition: IDLE cannot jump directly to PAID or RECORDING
    with pytest.raises(ValueError) as exc:
        repo.transition_state(scan_sess.id, SessionState.RECORDING, reason="Illegal jump")
    assert "Illegal state transition" in str(exc.value)

    # Transition to SCANNING then illegal jump to RECORDING
    repo.transition_state(scan_sess.id, SessionState.SCANNING)
    with pytest.raises(ValueError) as exc2:
        repo.transition_state(scan_sess.id, SessionState.RECORDING)
    assert "Illegal state transition" in str(exc2.value)


def test_detection_tracker_unique_person_counting():
    """
    Verifies that the IoUTracker correctly maintains persistent track IDs across 30 frames
    for the same person without overcounting, and assigns a new track ID when a second person enters.
    """
    tracker = IoUTracker(max_lost_frames=10, iou_threshold=0.3)

    # Frame 1 to 30: Person A walks slightly around center
    for i in range(30):
        jitter = (i % 5) * 0.005
        detections = [{
            "class_name": "person",
            "confidence": 0.88,
            "bbox": [0.2 + jitter, 0.2, 0.6 + jitter, 0.8]
        }]
        tracked = tracker.update(detections)
        assert len(tracked) == 1
        assert tracked[0]["track_id"] == 1  # Track ID must remain 1 across all 30 frames

    # Unique person count must be exactly 1
    assert len(tracker.unique_person_ids) == 1

    # Frame 31: Person B enters in a completely different quadrant
    frame_with_two = [
        {
            "class_name": "person",
            "confidence": 0.89,
            "bbox": [0.22, 0.2, 0.62, 0.8]  # Person A
        },
        {
            "class_name": "person",
            "confidence": 0.91,
            "bbox": [0.75, 0.1, 0.95, 0.7]  # Person B
        }
    ]
    tracked_two = tracker.update(frame_with_two)
    assert len(tracked_two) == 2
    assert len(tracker.unique_person_ids) == 2


def test_negative_stock_rejection(test_db_session):
    """
    Verifies that deducting more stock than available is rejected with an exception,
    and leaves inventory balances intact.
    """
    session, _ = test_db_session
    inv_repo = InventoryRepository(session)

    # Available stock is 10
    inv = inv_repo.get_or_create(product_id=101, owner_id=1)
    assert inv.on_hand == 10

    # Attempting to deduct 15 units must fail
    with pytest.raises(ValueError) as exc_info:
        inv_repo.deduct_stock(product_id=101, owner_id=1, qty=15, reason="SALE")

    assert "Insufficient stock" in str(exc_info.value)
    # Verify stock remained untouched at 10
    session.rollback()
    refreshed_inv = inv_repo.get_or_create(product_id=101, owner_id=1)
    assert refreshed_inv.on_hand == 10


def test_idempotent_payment_verification(monkeypatch, test_db_session):
    """
    Verifies that calling verify_and_settle_payment twice with the same transaction_ref
    only deducts inventory once and returns an idempotent response on subsequent calls.
    """
    session, _ = test_db_session
    from backend.database import get_db_session as real_get_db_session
    from contextlib import contextmanager

    # Point get_db_session to this test's isolated session
    @contextmanager
    def mock_db_session():
        yield session

    monkeypatch.setattr("backend.services.payment_service.get_db_session", mock_db_session)

    txn_ref = "TXN-IDEMPOTENT-TEST-001"
    cart = [{"product_id": 101, "sku": "SKU-TEST-MILK", "name": "Organic Test Milk", "quantity": 2}]

    # First settlement
    res1 = verify_and_settle_payment(
        transaction_ref=txn_ref,
        amount=90.0,
        payment_method="UPI_QR",
        cart_items=cart
    )
    assert res1["status"] == "SUCCESS"
    assert res1["verified"] is True

    # Inventory must now be 10 - 2 = 8
    inv = session.query(Inventory).filter_by(product_id=101, owner_id=1).one()
    assert inv.on_hand == 8

    # Second settlement with identical transaction_ref
    res2 = verify_and_settle_payment(
        transaction_ref=txn_ref,
        amount=90.0,
        payment_method="UPI_QR",
        cart_items=cart
    )
    assert res2["status"] == "SUCCESS"
    assert res2["verified"] is True
    assert res2.get("idempotent") is True

    # Inventory MUST still be 8 (never double deducted!)
    inv_after = session.query(Inventory).filter_by(product_id=101, owner_id=1).one()
    assert inv_after.on_hand == 8


def test_atomic_settlement_forced_failure_rollback(monkeypatch, test_db_session):
    """
    Verifies that a forced failure during payment settlement rolls back the entire
    transaction atomically, leaving 0 partial records in sales, sale_items, or inventory_movements.
    """
    session, _ = test_db_session
    from contextlib import contextmanager

    @contextmanager
    def mock_db_session():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    monkeypatch.setattr("backend.services.payment_service.get_db_session", mock_db_session)

    # Verify initial counts
    sales_before = session.query(Sale).count()
    movements_before = session.query(InventoryMovement).count()
    inv_before = session.query(Inventory).filter_by(product_id=101).one().on_hand

    # Cart requesting 20 units (greater than available stock 10)
    oversized_cart = [{"product_id": 101, "sku": "SKU-TEST-MILK", "quantity": 20}]

    with pytest.raises(ValueError):
        verify_and_settle_payment(
            transaction_ref="TXN-FAIL-ATOMIC-001",
            amount=900.0,
            cart_items=oversized_cart
        )

    # Assert complete atomic rollback: no orphan rows
    assert session.query(Sale).count() == sales_before
    assert session.query(SaleItem).count() == 0
    assert session.query(InventoryMovement).count() == movements_before
    assert session.query(Inventory).filter_by(product_id=101).one().on_hand == inv_before


def test_end_to_end_scanner_to_record_flow(monkeypatch, test_db_session):
    """
    End-to-end Smoke Path:
    Scan -> Basket -> Pay -> Auto-Transition -> Live Record -> End Session
    """
    session, _ = test_db_session
    import base64
    import io
    from PIL import Image
    from contextlib import contextmanager
    from backend.app import create_app

    @contextmanager
    def mock_db_session():
        yield session

    monkeypatch.setattr("backend.services.payment_service.get_db_session", mock_db_session)
    monkeypatch.setattr("backend.services.state_machine.get_db_session", mock_db_session)
    monkeypatch.setattr("backend.routes.record.get_db_session", mock_db_session)

    app = create_app({"TESTING": True})
    client = app.test_client()

    # 1. State starts at IDLE or initializes
    st_res = client.get("/api/session/state")
    assert st_res.status_code == 200

    # 2. Scanner CV recognition
    rec_res = client.post("/api/scanner/recognize", json={"barcode": "SKU-TEST-MILK"})
    assert rec_res.status_code == 200

    # 3. Generate Payment QR
    qr_res = client.post("/api/payment/generate-qr", json={"amount": 45.0, "purpose": "pos_checkout"})
    assert qr_res.status_code == 200
    qr_data = qr_res.get_json()
    assert "upi_uri" in qr_data

    # State is now PAYMENT_PENDING
    state_res = client.get("/api/session/state")
    assert state_res.get_json()["state"] == "PAYMENT_PENDING"

    # 4. Settle payment
    settle_res = client.post("/api/payment/verify", json={
        "transaction_ref": qr_data["transaction_ref"],
        "amount": 45.0,
        "payment_method": "UPI_QR",
        "cart_items": [{"product_id": 101, "sku": "SKU-TEST-MILK", "quantity": 1}]
    })
    assert settle_res.status_code == 200
    assert settle_res.get_json()["status"] == "SUCCESS"

    # State is now PAID
    paid_state = client.get("/api/session/state").get_json()
    assert paid_state["state"] == "PAID"

    # 5. Auto-navigates and transitions to RECORDING
    rec_start = client.post("/api/record/start")
    assert rec_start.status_code == 200
    assert rec_start.get_json()["state"] == "RECORDING"

    # 6. Stream frame to detector
    img = Image.new("RGB", (320, 240), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_img = base64.b64encode(buf.getvalue()).decode()

    frame_res = client.post("/api/record/frame", json={"image_data": b64_img, "blur_faces": True})
    assert frame_res.status_code == 200
    frame_data = frame_res.get_json()
    assert frame_data["status"] == "success"
    assert "privacy_notice" in frame_data

    # 7. End session
    stop_res = client.post("/api/record/stop")
    assert stop_res.status_code == 200
    assert stop_res.get_json()["state"] == "IDLE"
    assert "summary" in stop_res.get_json()

