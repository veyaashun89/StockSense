import datetime
import uuid
from typing import Dict, Any, List, Optional
from backend.database import get_db

def get_incoming_units_by_sku(shop_id: int = 1) -> Dict[str, int]:
    """
    Returns total units currently in transit across Submitted, Confirmed, or Dispatched purchase orders.
    Prevents double-ordering in the reorder planner.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT poi.sku, COALESCE(SUM(poi.quantity - COALESCE(poi.received_quantity, 0)), 0) as incoming_qty
        FROM purchase_order_items poi
        JOIN purchase_orders po ON poi.po_id = po.id
        WHERE po.shop_id = ? AND po.status IN ('Submitted', 'Confirmed', 'Dispatched')
        GROUP BY poi.sku
    """, (shop_id,))
    rows = cursor.fetchall()
    return {row["sku"].upper(): int(row["incoming_qty"] or 0) for row in rows}

def create_purchase_order(
    items: List[Dict[str, Any]],
    wholesaler_id: Optional[int] = None,
    notes: Optional[str] = None,
    shop_id: int = 1
) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    if not items:
        raise ValueError("Cannot create purchase order with zero items.")

    po_number = f"PO-{datetime.date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    total_amount = sum(float(it.get("quantity", 0)) * float(it.get("unit_cost", 0)) for it in items)

    cursor.execute("""
        INSERT INTO purchase_orders (po_number, shop_id, wholesaler_id, status, total_amount, notes)
        VALUES (?, ?, ?, 'Submitted', ?, ?)
    """, (po_number, shop_id, wholesaler_id, round(total_amount, 2), notes))

    po_id = cursor.lastrowid

    for it in items:
        cursor.execute("""
            INSERT INTO purchase_order_items (po_id, product_id, sku, product_name, quantity, unit_cost, total_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            po_id, it["product_id"], it["sku"], it["product_name"],
            int(it["quantity"]), float(it["unit_cost"]),
            round(int(it["quantity"]) * float(it["unit_cost"]), 2)
        ))

    db.commit()
    return get_purchase_order(po_id)

def get_purchase_order(po_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT po.*, u.name as wholesaler_name, s.name as shop_name
        FROM purchase_orders po
        LEFT JOIN users u ON po.wholesaler_id = u.id
        LEFT JOIN shops s ON po.shop_id = s.id
        WHERE po.id = ?
    """, (po_id,))
    po_row = cursor.fetchone()
    if not po_row:
        return None

    po = dict(po_row)
    cursor.execute("""
        SELECT * FROM purchase_order_items WHERE po_id = ?
    """, (po_id,))
    po["items"] = [dict(r) for r in cursor.fetchall()]
    return po

def list_purchase_orders(status: Optional[str] = None, shop_id: Optional[int] = None, wholesaler_id: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    query = """
        SELECT po.*, u.name as wholesaler_name, s.name as shop_name,
               (SELECT COUNT(*) FROM purchase_order_items WHERE po_id = po.id) as item_count,
               (SELECT SUM(quantity) FROM purchase_order_items WHERE po_id = po.id) as total_units
        FROM purchase_orders po
        LEFT JOIN users u ON po.wholesaler_id = u.id
        LEFT JOIN shops s ON po.shop_id = s.id
        WHERE 1=1
    """
    params = []
    if status and status != "all":
        query += " AND po.status = ?"
        params.append(status)
    if shop_id:
        query += " AND po.shop_id = ?"
        params.append(shop_id)
    if wholesaler_id:
        query += " AND (po.wholesaler_id = ? OR po.wholesaler_id IS NULL)"
        params.append(wholesaler_id)

    query += " ORDER BY po.created_at DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

def update_purchase_order_status(po_id: int, new_status: str, received_quantities: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    valid_statuses = {"Draft", "Submitted", "Confirmed", "Dispatched", "Delivered", "Rejected", "Cancelled"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(valid_statuses))}")

    cursor.execute("SELECT * FROM purchase_orders WHERE id = ?", (po_id,))
    po = cursor.fetchone()
    if not po:
        raise ValueError(f"Purchase order {po_id} not found.")

    old_status = po["status"]
    cursor.execute("UPDATE purchase_orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, po_id))

    # If transitioning to Delivered: receipt stock into products table & log movement
    if new_status == "Delivered" and old_status != "Delivered":
        cursor.execute("SELECT * FROM purchase_order_items WHERE po_id = ?", (po_id,))
        items = cursor.fetchall()
        for it in items:
            recv_qty = it["quantity"]
            if received_quantities and str(it["id"]) in received_quantities:
                recv_qty = int(received_quantities[str(it["id"])])

            cursor.execute("UPDATE purchase_order_items SET received_quantity = ? WHERE id = ?", (recv_qty, it["id"]))

            # Add to stock
            cursor.execute("UPDATE products SET current_stock = current_stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (recv_qty, it["product_id"]))
            cursor.execute("SELECT current_stock FROM products WHERE id = ?", (it["product_id"],))
            new_bal = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO inventory_movements (shop_id, product_id, movement_type, quantity, balance_after, reason)
                VALUES (?, ?, 'PO_DELIVERY', ?, ?, ?)
            """, (po["shop_id"], it["product_id"], recv_qty, new_bal, f"Receipt of PO {po['po_number']}"))

    db.commit()
    return get_purchase_order(po_id)
