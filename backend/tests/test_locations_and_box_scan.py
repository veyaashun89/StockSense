import pytest
import numpy as np
from PIL import Image
import zxingcpp
from backend.app import create_app
from backend.database import init_db
from backend.repositories.location_repository import LocationRepository
from backend.services.location_service import seed_demo_locations, process_box_scan
from backend.services.alert_service import list_alerts

@pytest.fixture
def app_ctx():
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        yield app

def test_hierarchical_location_creation_and_listing(app_ctx):
    """
    Phase 3 Requirement:
    Add locations (shelf, bin, box) with parent links.
    """
    # 1. Create Shelf
    shelf = LocationRepository.create_location(
        name="Shelf Test-A1",
        location_type="shelf",
        barcode="LOC-TEST-SH1"
    )
    assert shelf["id"] is not None
    assert shelf["parent_id"] is None

    # 2. Create Bin under Shelf
    bin_loc = LocationRepository.create_location(
        name="Bin Test-B1",
        location_type="bin",
        barcode="LOC-TEST-BIN1",
        parent_id=shelf["id"]
    )
    assert bin_loc["parent_id"] == shelf["id"]

    # 3. Create Box under Bin
    box = LocationRepository.create_location(
        name="Box Test-X1",
        location_type="box",
        barcode="LOC-TEST-BOX1",
        parent_id=bin_loc["id"]
    )
    assert box["parent_id"] == bin_loc["id"]

    # List locations and verify hierarchy
    locs = LocationRepository.list_locations()
    box_entry = next((l for l in locs if l["id"] == box["id"]), None)
    assert box_entry is not None
    assert box_entry["parent_name"] == "Bin Test-B1"
    assert box_entry["location_type"] == "box"

def test_box_scan_reconciliation_and_mismatch_alert(app_ctx):
    """
    Phase 3 Requirement:
    Box scan flow compares count with expected stock for that location.
    Creates an alert on mismatch.
    """
    # Create test box
    box = LocationRepository.create_location(
        name="Box Audit-001",
        location_type="box",
        barcode="LOC-BOX-AUDIT"
    )
    box_id = box["id"]

    # Set expected quantity: 6 units of SKU-MLK-01
    LocationRepository.set_location_stock(box_id, "SKU-MLK-01", expected_qty=6)

    # 1. Test Match Scenario: Scanned exactly 6
    match_result = LocationRepository.reconcile_box_counts(box_id, {"SKU-MLK-01": 6})
    assert match_result["mismatch_count"] == 0
    assert match_result["reconciled_items"][0]["status"] == "MATCH"

    # 2. Test Mismatch Shortage: Physical scan only found 4 items (2 missing/spoilage)
    mismatch_result = LocationRepository.reconcile_box_counts(box_id, {"SKU-MLK-01": 4})
    assert mismatch_result["mismatch_count"] == 1
    assert mismatch_result["reconciled_items"][0]["status"] == "MISMATCH_SHORTAGE"
    assert mismatch_result["reconciled_items"][0]["difference"] == -2
    assert len(mismatch_result["alerts_created"]) >= 1

    # Verify Alert was created in database
    alerts = list_alerts()
    matching_alert = next((a for a in alerts if "Box Audit-001" in a.get("title", "")), None)
    assert matching_alert is not None
    assert matching_alert["severity"] == "HIGH"
    assert "Expected 6, Scanned 4 (-2)" in matching_alert["message"]

def test_box_scan_from_image_flow(app_ctx):
    """
    Phase 3 Requirement:
    Detect each item, decode its code first, track and reconcile with location stock.
    """
    box = LocationRepository.create_location(
        name="Box Image-Test",
        location_type="box",
        barcode="LOC-BOX-IMG"
    )
    box_id = box["id"]
    LocationRepository.set_location_stock(box_id, "SKU-MLK-01", expected_qty=1)

    # Generate an image with QR code for SKU-MLK-01
    bc = zxingcpp.create_barcode("SKU-MLK-01", zxingcpp.BarcodeFormat.QRCode)
    arr = np.array(zxingcpp.write_barcode_to_image(bc))
    img = Image.fromarray(arr)

    result = process_box_scan(box_id, img)
    assert result["status"] == "success"
    assert result["scanned_counts"].get("SKU-MLK-01") == 1
    assert result["reconciliation"]["mismatch_count"] == 0
