import pytest
from backend.services.forecasting_service import forecast_demand, forecast_demand_weekly
from backend.services.reorder_service import calculate_product_reorder, generate_reorder_plan
from backend.services.priority_service import evaluate_priority
from backend.services.gst_service import validate_and_preview_gst_csv
from backend.services.alert_service import evaluate_and_generate_alerts, list_alerts
from backend.services.auth_service import authenticate_user, switch_demo_role
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_hard_shelf_life_cap():
    # Perishable product with short shelf life
    # Shelf life: 5 days, Lead time: 2 days, Buffer: 1 day -> Usable window = 2 days
    # Demand = 10 units/day -> Max sellable = 20 units. Current stock = 5 units -> Cap = 15 units
    dummy_perishable = {
        "id": 1,
        "sku": "SKU-BER-06",
        "name": "Fresh Strawberries",
        "category": "Dairy & Fresh",
        "current_stock": 5,
        "unit_cost": 2.0,
        "selling_price": 4.0,
        "lead_time_days": 2,
        "is_perishable": 1,
        "shelf_life_days": 5,
        "min_order_qty": 5,
        "pack_size": 5,
        "safety_buffer_days": 1
    }
    plan = calculate_product_reorder(dummy_perishable, coverage_days=14, shelf_life_buffer_days=1)
    assert plan["is_perishable"] is True
    assert plan["usable_selling_window"] == 2
    assert plan["shelf_life_cap"] is not None

def test_shelf_life_incompatibility():
    # Lead time (10d) >= Shelf life (4d) -> Critical supplier delivery risk
    incompatible_item = {
        "id": 7,
        "sku": "SKU-SUS-07",
        "name": "Sushi Tuna",
        "category": "Dairy & Fresh",
        "current_stock": 0,
        "unit_cost": 8.0,
        "selling_price": 16.0,
        "lead_time_days": 10,
        "is_perishable": 1,
        "shelf_life_days": 4,
        "min_order_qty": 5,
        "pack_size": 5,
        "safety_buffer_days": 1
    }
    plan = calculate_product_reorder(incompatible_item, coverage_days=14)
    assert plan["shelf_life_incompatible"] is True
    assert plan["recommended_reorder_qty"] == 0
    assert "cannot guarantee freshness" in plan["shelf_life_note"].lower()

def test_incoming_purchase_orders_prevent_double_ordering():
    # Product with 20 units in transit
    dummy_item = {
        "id": 1,
        "sku": "SKU-MLK-01",
        "name": "Fresh Milk",
        "category": "Dairy & Fresh",
        "current_stock": 5,
        "unit_cost": 2.0,
        "selling_price": 4.0,
        "lead_time_days": 2,
        "is_perishable": 0,
        "shelf_life_days": None,
        "min_order_qty": 1,
        "pack_size": 1,
        "safety_buffer_days": 2
    }
    # With 0 incoming
    plan_no_incoming = calculate_product_reorder(dummy_item, incoming_units_map={"SKU-MLK-01": 0})
    # With 30 incoming
    plan_with_incoming = calculate_product_reorder(dummy_item, incoming_units_map={"SKU-MLK-01": 30})
    
    assert plan_with_incoming["inventory_position"] == 35
    assert plan_with_incoming["recommended_reorder_qty"] < plan_no_incoming["recommended_reorder_qty"]

def test_weekly_forecasting():
    res = forecast_demand_weekly(1, horizon_weeks=4, window_days=60)
    assert res["forecast_granularity"] == "weekly"
    assert len(res["weekly_forecast"]) == 4
    for w in res["weekly_forecast"]:
        assert "predicted_units" in w
        assert "lower_bound" in w
        assert "upper_bound" in w
        assert w["lower_bound"] <= w["upper_bound"]

def test_gst_validation():
    valid_gst_csv = """invoice_no,invoice_date,supply_type,gstin_counterparty,hsn_code,item_description,sku,quantity,taxable_value,gst_rate,total_value
INV-101,2026-10-22,outward,27AAAAA0000A1Z5,0401,Fresh Milk,SKU-MLK-01,10,40.0,0,40.0
INV-102,invalid-date,outward,27AAAAA0000A1Z5,0401,Fresh Milk,SKU-MLK-01,10,40.0,0,40.0
"""
    res = validate_and_preview_gst_csv(valid_gst_csv, "test_gst.csv")
    assert res["valid_count"] == 1
    assert res["invalid_count"] == 1
    assert "Invalid date" in res["invalid_rows"][0]["reason"]

def test_automated_alerts_deduplication():
    res1 = evaluate_and_generate_alerts(shop_id=1)
    initial_alerts = list_alerts(shop_id=1)
    initial_count = len(initial_alerts)

    # Second evaluation should deduplicate and NOT create duplicate open alerts!
    res2 = evaluate_and_generate_alerts(shop_id=1)
    after_alerts = list_alerts(shop_id=1)
    assert len(after_alerts) == initial_count
    assert res2["new_alerts_created"] == 0

def test_role_based_auth():
    retailer = switch_demo_role("retailer")
    wholesaler = switch_demo_role("wholesaler")
    admin = switch_demo_role("admin")

    assert retailer["role"] == "retailer"
    assert wholesaler["role"] == "wholesaler"
    assert admin["role"] == "admin"

def test_cv_product_recognition():
    """Verify Computer Vision product recognizer matches barcodes and visual labels."""
    from backend.services.vision_service import recognize_product_cv

    res = recognize_product_cv(barcode_text="MLK-001", detected_label="milk dairy")
    assert res["matched"] is True
    assert "product" in res
    assert res["confidence"] >= 0.65
    assert "visual_signature" in res or "confidence_percentage" in res

def test_dynamic_upi_payment_and_settlement():
    """Verify Dynamic UPI payment QR generation and instant stock reconciliation."""
    from backend.services.payment_service import create_payment_request, verify_and_settle_payment
    from backend.database import get_db

    qr_res = create_payment_request(amount=108.0, purpose="pos_test")
    assert qr_res["status"] == "PENDING"
    assert "upi://pay?" in qr_res["upi_uri"]
    assert "<svg" in qr_res["qr_svg"]

    # Verify settlement for 2 units
    settle_res = verify_and_settle_payment(
        transaction_ref=qr_res["transaction_ref"],
        amount=108.0,
        payment_method="UPI_QR",
        cart_items=[{"sku": "MLK-001", "quantity": 2}]
    )
    assert settle_res["status"] == "SUCCESS"
    assert settle_res["verified"] is True
    assert len(settle_res["processed_items"]) > 0

