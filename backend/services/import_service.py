"""
StockSense AI - Universal CSV & Excel Ingestion and Past Records Service
------------------------------------------------------------------------
Supports both CSV and Excel (.xlsx) imports for past sales ledgers and stock snapshots.
Includes:
- Dry-run audit mode (reports row counts and errors without modifying database)
- Strict validation: rejects negative quantities, unknown SKUs, and invalid dates
- Detailed rejection diagnostics (row index, rejected field, specific reason)
- Writes audit trail to import_batches
- Writes inventory movements for all stock adjustments (Rule 5 compliance)
- Past records queries (sales by day/week, stock movements, and batch audits)
"""

import io
import csv
import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from dateutil import parser as date_parser
import openpyxl

from backend.database import get_db, get_db_session
from backend.models.orm_models import (
    ImportBatch, Sale, Product, Inventory, InventoryMovement, Location, LocationStock
)

def extract_rows_from_file_bytes(file_bytes: bytes, filename: str) -> List[List[str]]:
    """Extracts 2D text matrix from CSV or Excel (.xlsx / .xls)."""
    fn = filename.lower()
    if fn.endswith(".xlsx") or fn.endswith(".xlsm") or fn.endswith(".xltx"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        rows = []
        for r in sheet.iter_rows():
            row_vals = [str(cell.value or "").strip() for cell in r]
            if any(v for v in row_vals):
                rows.append(row_vals)
        return rows
    else:
        # Assume CSV / TSV / text
        content = file_bytes.decode("utf-8", errors="replace")
        delimiter = "\t" if "\t" in content.split("\n")[0] else ","
        reader = csv.reader(io.StringIO(content.strip()), delimiter=delimiter)
        return [[c.strip() for c in r] for r in reader if any(c.strip() for c in r)]

def validate_date_string(date_str: str) -> Optional[str]:
    """Validates and normalizes date string to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        dt = date_parser.parse(date_str.strip())
        return dt.date().isoformat()
    except Exception:
        return None

def process_sales_import(
    file_bytes: bytes,
    filename: str,
    dry_run: bool = False,
    shop_id: int = 1,
    owner_id: int = 1
) -> Dict[str, Any]:
    """
    Ingests past sales ledger from CSV or Excel.
    Expected headers: sku, sale_date, quantity_sold (optional: unit_price)
    """
    rows = extract_rows_from_file_bytes(file_bytes, filename)
    if not rows:
        return {"error": "Empty file content", "total_rows": 0, "valid_count": 0, "rejected_count": 0, "rejected_rows": []}

    headers = [h.lower() for h in rows[0]]
    if "sku" not in headers or "quantity_sold" not in headers:
        return {
            "error": "Missing required columns. Expected at least 'sku' and 'quantity_sold'",
            "headers_found": headers
        }

    sku_idx = headers.index("sku")
    qty_idx = headers.index("quantity_sold")
    date_idx = headers.index("sale_date") if "sale_date" in headers else None

    with get_db_session() as session:
        catalog = {
            p.sku.upper(): {
                "id": p.id,
                "sku": p.sku,
                "retail_price_paise": p.retail_price_paise or int((p.selling_price or 0.0) * 100),
                "current_stock": p.current_stock
            }
            for p in session.query(Product).filter(Product.is_active == 1).all()
        }

    valid_rows = []
    rejected_rows = []
    batch_uuid = str(uuid.uuid4())

    for idx, row in enumerate(rows[1:], start=2):
        if len(row) <= max(sku_idx, qty_idx):
            rejected_rows.append({"row": idx, "reason": "Insufficient columns in row", "data": row})
            continue

        raw_sku = row[sku_idx].upper().strip()
        raw_qty = row[qty_idx].strip()
        raw_date = row[date_idx].strip() if date_idx is not None and len(row) > date_idx else datetime.date.today().isoformat()

        # Check unknown SKU
        if raw_sku not in catalog:
            rejected_rows.append({"row": idx, "sku": raw_sku, "reason": f"Unknown SKU: '{raw_sku}' not in active catalog", "data": row})
            continue

        # Check quantity integer & non-negative
        try:
            qty = int(float(raw_qty))
            if qty <= 0:
                rejected_rows.append({"row": idx, "sku": raw_sku, "quantity": raw_qty, "reason": "Quantity must be strictly positive (rejected non-positive quantity)", "data": row})
                continue
        except ValueError:
            rejected_rows.append({"row": idx, "sku": raw_sku, "quantity": raw_qty, "reason": f"Invalid integer quantity: '{raw_qty}'", "data": row})
            continue

        # Check valid date
        normalized_date = validate_date_string(raw_date)
        if not normalized_date:
            rejected_rows.append({"row": idx, "sku": raw_sku, "date": raw_date, "reason": f"Invalid date format: '{raw_date}'", "data": row})
            continue

        prod_info = catalog[raw_sku]
        unit_price_paise = prod_info["retail_price_paise"]
        total_paise = unit_price_paise * qty

        valid_rows.append({
            "product_id": prod_info["id"],
            "sku": raw_sku,
            "sale_date": normalized_date,
            "quantity_sold": qty,
            "unit_price_paise": unit_price_paise,
            "total_paise": total_paise
        })

    # Dry-run audit response
    if dry_run:
        return {
            "status": "dry_run",
            "filename": filename,
            "total_rows": len(rows) - 1,
            "valid_count": len(valid_rows),
            "rejected_count": len(rejected_rows),
            "rejected_rows": rejected_rows,
            "sample_valid": valid_rows[:10]
        }

    # Commit if not dry run
    if valid_rows:
        with get_db_session() as session:
            # Create audit batch
            batch = ImportBatch(
                id=batch_uuid,
                filename=filename,
                batch_type="SALES",
                total_rows=len(rows) - 1,
                valid_rows=len(valid_rows),
                invalid_rows=len(rejected_rows),
                status="COMPLETED"
            )
            session.add(batch)

            for vr in valid_rows:
                s = Sale(
                    owner_id=owner_id,
                    shop_id=shop_id,
                    product_id=vr["product_id"],
                    sku=vr["sku"],
                    quantity_sold=vr["quantity_sold"],
                    sale_date=vr["sale_date"],
                    subtotal_paise=vr["total_paise"],
                    total_paise=vr["total_paise"],
                    payment_status="PAID",
                    source="batch_import",
                    import_batch_id=batch_uuid
                )
                session.add(s)

            session.commit()

    return {
        "status": "committed",
        "batch_id": batch_uuid,
        "filename": filename,
        "total_rows": len(rows) - 1,
        "imported_count": len(valid_rows),
        "rejected_count": len(rejected_rows),
        "rejected_rows": rejected_rows
    }

def process_stock_import(
    file_bytes: bytes,
    filename: str,
    dry_run: bool = False,
    shop_id: int = 1,
    owner_id: int = 1
) -> Dict[str, Any]:
    """
    Ingests current stock snapshot from CSV or Excel.
    Enforces Rule 5: Every stock change goes through inventory service and writes a movement row.
    Expected headers: sku, quantity_on_hand (optional: location_barcode or location_id)
    """
    rows = extract_rows_from_file_bytes(file_bytes, filename)
    if not rows:
        return {"error": "Empty file content", "total_rows": 0, "valid_count": 0, "rejected_count": 0, "rejected_rows": []}

    headers = [h.lower() for h in rows[0]]
    if "sku" not in headers or not any(h in headers for h in ["quantity_on_hand", "quantity", "stock"]):
        return {
            "error": "Missing required columns. Expected at least 'sku' and 'quantity_on_hand'",
            "headers_found": headers
        }

    sku_idx = headers.index("sku")
    qty_idx = headers.index("quantity_on_hand") if "quantity_on_hand" in headers else (headers.index("quantity") if "quantity" in headers else headers.index("stock"))
    loc_idx = headers.index("location") if "location" in headers else (headers.index("location_barcode") if "location_barcode" in headers else None)

    with get_db_session() as session:
        catalog = {
            p.sku.upper(): {
                "id": p.id,
                "sku": p.sku,
                "current_stock": p.current_stock
            }
            for p in session.query(Product).filter(Product.is_active == 1).all()
        }
        locations = {l.barcode.upper(): l.id for l in session.query(Location).filter(Location.barcode.isnot(None)).all()}

    valid_rows = []
    rejected_rows = []
    batch_uuid = str(uuid.uuid4())

    for idx, row in enumerate(rows[1:], start=2):
        if len(row) <= max(sku_idx, qty_idx):
            rejected_rows.append({"row": idx, "reason": "Insufficient columns in row", "data": row})
            continue

        raw_sku = row[sku_idx].upper().strip()
        raw_qty = row[qty_idx].strip()
        raw_loc = row[loc_idx].strip().upper() if loc_idx is not None and len(row) > loc_idx else None

        if raw_sku not in catalog:
            rejected_rows.append({"row": idx, "sku": raw_sku, "reason": f"Unknown SKU: '{raw_sku}' not in active catalog", "data": row})
            continue

        try:
            qty = int(float(raw_qty))
            if qty < 0:
                rejected_rows.append({"row": idx, "sku": raw_sku, "quantity": raw_qty, "reason": "Negative stock quantities are strictly rejected", "data": row})
                continue
        except ValueError:
            rejected_rows.append({"row": idx, "sku": raw_sku, "quantity": raw_qty, "reason": f"Invalid integer quantity: '{raw_qty}'", "data": row})
            continue

        loc_id = locations.get(raw_loc) if raw_loc else None
        prod_info = catalog[raw_sku]

        valid_rows.append({
            "product_id": prod_info["id"],
            "sku": raw_sku,
            "new_stock": qty,
            "old_stock": prod_info["current_stock"],
            "diff": qty - prod_info["current_stock"],
            "location_id": loc_id
        })

    if dry_run:
        return {
            "status": "dry_run",
            "filename": filename,
            "total_rows": len(rows) - 1,
            "valid_count": len(valid_rows),
            "rejected_count": len(rejected_rows),
            "rejected_rows": rejected_rows,
            "sample_valid": valid_rows[:10]
        }

    # Commit with Inventory Movement rows
    if valid_rows:
        with get_db_session() as session:
            batch = ImportBatch(
                id=batch_uuid,
                filename=filename,
                batch_type="STOCK",
                total_rows=len(rows) - 1,
                valid_rows=len(valid_rows),
                invalid_rows=len(rejected_rows),
                status="COMPLETED"
            )
            session.add(batch)

            for vr in valid_rows:
                prod = session.query(Product).filter(Product.id == vr["product_id"]).first()
                if prod:
                    prod.current_stock = vr["new_stock"]
                    # Rule 5: Write Movement row for every stock change
                    movement = InventoryMovement(
                        shop_id=shop_id,
                        owner_id=owner_id,
                        product_id=prod.id,
                        delta=vr["diff"],
                        quantity=vr["diff"],
                        balance_after=vr["new_stock"],
                        movement_type="SNAPSHOT_ADJUSTMENT",
                        reason="BATCH_STOCK_IMPORT",
                        reference=f"batch_{batch_uuid[:8]}"
                    )
                    session.add(movement)

                    # Update location stock if location was specified
                    if vr["location_id"]:
                        loc_stock = session.query(LocationStock).filter(
                            LocationStock.location_id == vr["location_id"],
                            LocationStock.product_id == prod.id
                        ).first()
                        if loc_stock:
                            loc_stock.actual_quantity = vr["new_stock"]
                            loc_stock.last_counted_at = datetime.datetime.utcnow()

            session.commit()

    return {
        "status": "committed",
        "batch_id": batch_uuid,
        "filename": filename,
        "total_rows": len(rows) - 1,
        "imported_count": len(valid_rows),
        "rejected_count": len(rejected_rows),
        "rejected_rows": rejected_rows
    }

def get_past_sales_records(
    group_by: str = "day",  # 'day' or 'week'
    sku: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieves past sales records aggregated by day or ISO calendar week."""
    db = get_db()
    cursor = db.cursor()

    params = []
    where_clauses = ["1=1"]
    if sku:
        where_clauses.append("p.sku = ?")
        params.append(sku.upper())

    where_sql = " AND ".join(where_clauses)

    if group_by == "week":
        # Group sales into ISO weeks
        query = f"""
            SELECT 
                strftime('%Y-W%W', s.sale_date) as period,
                s.sku,
                p.name as product_name,
                SUM(s.quantity_sold) as total_units,
                SUM(s.total_paise) as total_paise,
                COUNT(s.id) as transaction_count
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE {where_sql}
            GROUP BY period, s.sku
            ORDER BY period DESC, total_units DESC
            LIMIT ?
        """
    else:
        # Default by day
        query = f"""
            SELECT 
                s.sale_date as period,
                s.sku,
                p.name as product_name,
                SUM(s.quantity_sold) as total_units,
                SUM(s.total_paise) as total_paise,
                COUNT(s.id) as transaction_count
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE {where_sql}
            GROUP BY s.sale_date, s.sku
            ORDER BY s.sale_date DESC, total_units DESC
            LIMIT ?
        """

    params.append(limit)
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def get_stock_movements_history(
    sku: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieves immutable audit trail of inventory movements."""
    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT 
            m.id,
            m.created_at,
            m.product_id,
            p.sku,
            p.name as product_name,
            m.delta,
            m.balance_after,
            m.reason,
            m.movement_type,
            m.reference
        FROM inventory_movements m
        JOIN products p ON m.product_id = p.id
    """
    params = []
    if sku:
        query += " WHERE p.sku = ?"
        params.append(sku.upper())

    query += " ORDER BY m.id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def get_import_batches_list() -> List[Dict[str, Any]]:
    """Retrieves all past import batches for audit verification."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM import_batches ORDER BY created_at DESC LIMIT 50")
    return [dict(row) for row in cursor.fetchall()]
