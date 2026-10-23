import csv
import io
import datetime
from typing import Dict, Any, List, Optional
from backend.database import get_db

def ingest_stock_snapshot_csv(file_content: str, filename: str, shop_id: int = 1) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    reader = csv.reader(io.StringIO(file_content.strip()))
    try:
        headers = [h.strip().lower() for h in next(reader, [])]
    except Exception as e:
        return {"error": str(e), "is_valid": False}

    if "sku" not in headers or "quantity_on_hand" not in headers:
        return {"error": "Missing required columns: sku, quantity_on_hand", "is_valid": False}

    sku_idx = headers.index("sku")
    qty_idx = headers.index("quantity_on_hand")
    date_idx = headers.index("as_of_date") if "as_of_date" in headers else None
    batch_idx = headers.index("batch_id") if "batch_id" in headers else None
    exp_idx = headers.index("expiry_date") if "expiry_date" in headers else None

    # Load active products
    cursor.execute("SELECT id, sku, current_stock, is_perishable FROM products WHERE shop_id = ? AND is_active = 1", (shop_id,))
    prod_map = {row["sku"].upper(): row for row in cursor.fetchall()}

    reconciled_products = 0
    batches_recorded = 0

    for row in reader:
        if not row or not any(f.strip() for f in row):
            continue
        raw_sku = row[sku_idx].strip().upper()
        raw_qty = row[qty_idx].strip()
        as_of = row[date_idx].strip() if date_idx is not None and len(row) > date_idx else datetime.date.today().isoformat()
        batch_id = row[batch_idx].strip() if batch_idx is not None and len(row) > batch_idx else f"BATCH-{datetime.date.today().strftime('%Y%m%d')}"
        exp_date = row[exp_idx].strip() if exp_idx is not None and len(row) > exp_idx and row[exp_idx].strip() else None

        if raw_sku not in prod_map:
            continue

        try:
            new_qty = int(float(raw_qty))
            if new_qty < 0:
                continue
        except ValueError:
            continue

        prod = prod_map[raw_sku]
        old_stock = prod["current_stock"]
        diff = new_qty - old_stock

        # Update product stock
        cursor.execute("UPDATE products SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_qty, prod["id"]))

        # Log movement audit
        if diff != 0:
            cursor.execute("""
                INSERT INTO inventory_movements (shop_id, product_id, movement_type, quantity, balance_after, reason)
                VALUES (?, ?, 'ADJUSTMENT', ?, ?, ?)
            """, (shop_id, prod["id"], diff, new_qty, f"Physical Stock Count Reconciliation (As of {as_of})"))

        # Record batch and expiry date if provided
        if exp_date:
            cursor.execute("""
                INSERT INTO stock_batches (shop_id, product_id, sku, batch_id, quantity, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (shop_id, prod["id"], raw_sku, batch_id, new_qty, exp_date))
            batches_recorded += 1

        reconciled_products += 1

    db.commit()
    return {
        "status": "success",
        "reconciled_products": reconciled_products,
        "batches_recorded": batches_recorded,
        "message": f"Successfully reconciled stock for {reconciled_products} products with movement audit tracking ({batches_recorded} batch expiries recorded)."
    }

def get_stock_batches(product_id: Optional[int] = None, shop_id: int = 1) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    query = """
        SELECT b.*, p.name as product_name, p.category, p.is_perishable
        FROM stock_batches b
        JOIN products p ON b.product_id = p.id
        WHERE b.shop_id = ?
    """
    params = [shop_id]
    if product_id:
        query += " AND b.product_id = ?"
        params.append(product_id)
    query += " ORDER BY b.expiry_date ASC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]
