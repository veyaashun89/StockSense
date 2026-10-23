import io
import pytest
import openpyxl
from backend.app import create_app
from backend.database import init_db, get_db
from backend.services.import_service import (
    process_sales_import,
    process_stock_import,
    get_past_sales_records,
    get_stock_movements_history,
    get_import_batches_list
)

@pytest.fixture
def app_ctx():
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        yield app

def test_sales_import_csv_validation_and_cleaning(app_ctx):
    """
    Phase 4 Requirement:
    Clean data: reject negative quantities, unknown SKUs, and invalid dates,
    and list each rejected row with its reason.
    """
    csv_content = """sku,sale_date,quantity_sold
SKU-MLK-01,2026-10-21,5
UNKNOWN-SKU-999,2026-10-21,2
SKU-MLK-01,2026-10-21,-3
SKU-MLK-01,not-a-valid-date,4
SKU-MLK-01,2026-10-22,8
"""
    result = process_sales_import(csv_content.encode("utf-8"), "test_sales.csv", dry_run=False)

    assert result["status"] == "committed"
    assert result["imported_count"] == 2  # 2 valid rows
    assert result["rejected_count"] == 3  # 3 rejected rows

    reasons = [r["reason"] for r in result["rejected_rows"]]
    assert any("Unknown SKU" in r for r in reasons)
    assert any("strictly positive" in r or "negative" in r for r in reasons)
    assert any("Invalid date" in r for r in reasons)

def test_sales_import_excel_format_and_dry_run(app_ctx):
    """
    Phase 4 Requirement:
    Excel (.xlsx) import with dry-run mode that reports row counts without writing.
    """
    # Create in-memory workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["sku", "sale_date", "quantity_sold"])
    ws.append(["SKU-MLK-01", "2026-10-20", 10])
    ws.append(["SKU-MLK-01", "2026-10-20", -5])  # Negative
    buf = io.BytesIO()
    wb.save(buf)
    file_bytes = buf.getvalue()

    import uuid
    test_fname = f"test_{uuid.uuid4().hex[:8]}.xlsx"

    # 1. Run in dry_run mode
    dry_res = process_sales_import(file_bytes, test_fname, dry_run=True)
    assert dry_res["status"] == "dry_run"
    assert dry_res["valid_count"] == 1
    assert dry_res["rejected_count"] == 1
    assert len(dry_res["rejected_rows"]) == 1

    # Verify no sales rows written with dry_run
    db = get_db()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM import_batches WHERE filename = ?", (test_fname,))
    assert c.fetchone()[0] == 0

    # 2. Run commit
    commit_res = process_sales_import(file_bytes, test_fname, dry_run=False)
    assert commit_res["status"] == "committed"
    assert commit_res["imported_count"] == 1
    assert commit_res["rejected_count"] == 1

def test_stock_import_movement_logging_rule5(app_ctx):
    """
    Phase 4 & Rule 5:
    Every stock change writes an inventory movement row.
    """
    csv_content = """sku,quantity_on_hand
SKU-MLK-01,75
"""
    result = process_stock_import(csv_content.encode("utf-8"), "stock_update.csv", dry_run=False)
    assert result["status"] == "committed"
    assert result["imported_count"] == 1

    # Verify product stock updated and movement row written
    movements = get_stock_movements_history(sku="SKU-MLK-01", limit=5)
    assert len(movements) >= 1
    latest_movement = movements[0]
    assert latest_movement["sku"] == "SKU-MLK-01"
    assert latest_movement["balance_after"] == 75
    assert latest_movement["reason"] == "BATCH_STOCK_IMPORT"

def test_past_sales_records_day_and_week(app_ctx):
    """
    Phase 4: Sales records query grouped by day and week.
    """
    day_records = get_past_sales_records(group_by="day", limit=20)
    assert isinstance(day_records, list)

    week_records = get_past_sales_records(group_by="week", limit=20)
    assert isinstance(week_records, list)
    if week_records:
        assert "W" in week_records[0]["period"]  # ISO week e.g. 2026-W42
