import sqlite3
from typing import Dict, Any, List, Optional
from backend.database import get_db

def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    page: int = 1,
    per_page: int = 100
) -> Dict[str, Any]:
    db = get_db()
    
    query = """
        SELECT 
            p.*,
            s.name as supplier_name,
            s.lead_time as supplier_lead_time,
            s.min_order_qty as supplier_min_order_qty,
            s.pack_size as supplier_pack_size
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.is_active = 1
    """
    params = []

    if search:
        query += " AND (p.name LIKE ? OR p.sku LIKE ? OR p.category LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term])

    if category and category != "all":
        query += " AND p.category = ?"
        params.append(category)

    # Validate sorting column
    valid_sort_cols = {
        "name": "p.name",
        "sku": "p.sku",
        "category": "p.category",
        "current_stock": "p.current_stock",
        "unit_cost": "p.unit_cost",
        "selling_price": "p.selling_price",
        "lead_time_days": "p.lead_time_days"
    }
    col = valid_sort_cols.get(sort_by, "p.name")
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    query += f" ORDER BY {col} {direction}"

    cursor = db.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    total = len(rows)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_rows = rows[start_idx:end_idx]

    products = [dict(row) for row in paginated_rows]
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
        "items": products
    }

def get_product(product_id_or_sku: Any) -> Optional[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    if isinstance(product_id_or_sku, int) or (isinstance(product_id_or_sku, str) and product_id_or_sku.isdigit()):
        cursor.execute("""
            SELECT p.*, s.name as supplier_name 
            FROM products p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = ?
        """, (int(product_id_or_sku),))
    else:
        cursor.execute("""
            SELECT p.*, s.name as supplier_name 
            FROM products p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.sku = ?
        """, (str(product_id_or_sku),))
    
    row = cursor.fetchone()
    return dict(row) if row else None

def create_product(data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    sku = str(data.get("sku", "")).strip().upper()
    name = str(data.get("name", "")).strip()
    category = str(data.get("category", "")).strip()
    current_stock = int(data.get("current_stock", 0))
    unit_cost = float(data.get("unit_cost", 0.0))
    selling_price = float(data.get("selling_price", 0.0))
    supplier_id = data.get("supplier_id")
    lead_time_days = int(data.get("lead_time_days", 7))
    is_perishable = 1 if data.get("is_perishable") else 0
    shelf_life_days = int(data["shelf_life_days"]) if data.get("shelf_life_days") is not None and str(data["shelf_life_days"]).strip() != "" else None
    min_order_qty = max(1, int(data.get("min_order_qty", 1)))
    pack_size = max(1, int(data.get("pack_size", 1)))
    safety_buffer_days = max(1, int(data.get("safety_buffer_days", 3)))

    if not sku:
        raise ValueError("Product SKU is required")
    if not name:
        raise ValueError("Product name is required")
    if not category:
        raise ValueError("Category is required")
    if current_stock < 0:
        raise ValueError("Current stock cannot be negative")
    if unit_cost < 0 or selling_price < 0:
        raise ValueError("Prices cannot be negative")
    if is_perishable and (shelf_life_days is None or shelf_life_days <= 0):
        raise ValueError("Perishable products require a positive shelf life in days")

    cursor.execute("""
        INSERT INTO products (
            sku, name, category, current_stock, unit_cost, selling_price,
            supplier_id, lead_time_days, is_perishable, shelf_life_days,
            min_order_qty, pack_size, safety_buffer_days
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sku, name, category, current_stock, unit_cost, selling_price,
        supplier_id, lead_time_days, is_perishable, shelf_life_days,
        min_order_qty, pack_size, safety_buffer_days
    ))

    product_id = cursor.lastrowid
    
    # Record initial inventory movement
    cursor.execute("""
        INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reason)
        VALUES (?, 'INITIAL', ?, ?, 'Initial inventory setup')
    """, (product_id, current_stock, current_stock))

    db.commit()
    return get_product(product_id)

def update_product(product_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()

    existing = get_product(product_id)
    if not existing:
        return None

    sku = str(data.get("sku", existing["sku"])).strip().upper()
    name = str(data.get("name", existing["name"])).strip()
    category = str(data.get("category", existing["category"])).strip()
    unit_cost = float(data.get("unit_cost", existing["unit_cost"]))
    selling_price = float(data.get("selling_price", existing["selling_price"]))
    supplier_id = data.get("supplier_id", existing["supplier_id"])
    lead_time_days = int(data.get("lead_time_days", existing["lead_time_days"]))
    is_perishable = 1 if data.get("is_perishable", existing["is_perishable"]) else 0
    shelf_life_days = data.get("shelf_life_days", existing["shelf_life_days"])
    if shelf_life_days is not None and str(shelf_life_days).strip() != "":
        shelf_life_days = int(shelf_life_days)
    else:
        shelf_life_days = None
    min_order_qty = max(1, int(data.get("min_order_qty", existing["min_order_qty"])))
    pack_size = max(1, int(data.get("pack_size", existing["pack_size"])))
    safety_buffer_days = max(1, int(data.get("safety_buffer_days", existing["safety_buffer_days"])))

    # Stock update handling
    new_stock = existing["current_stock"]
    if "current_stock" in data:
        new_stock = int(data["current_stock"])
        if new_stock < 0:
            raise ValueError("Stock quantity cannot be negative")
        diff = new_stock - existing["current_stock"]
        if diff != 0:
            cursor.execute("""
                INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reason)
                VALUES (?, 'ADJUSTMENT', ?, ?, 'Manual stock edit')
            """, (product_id, diff, new_stock))

    cursor.execute("""
        UPDATE products SET
            sku = ?, name = ?, category = ?, current_stock = ?,
            unit_cost = ?, selling_price = ?, supplier_id = ?,
            lead_time_days = ?, is_perishable = ?, shelf_life_days = ?,
            min_order_qty = ?, pack_size = ?, safety_buffer_days = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        sku, name, category, new_stock, unit_cost, selling_price,
        supplier_id, lead_time_days, is_perishable, shelf_life_days,
        min_order_qty, pack_size, safety_buffer_days, product_id
    ))
    db.commit()
    return get_product(product_id)

def delete_product(product_id: int) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    existing = get_product(product_id)
    if not existing:
        raise ValueError("Product not found")

    # Check sales history
    cursor.execute("SELECT COUNT(*) FROM sales WHERE product_id = ?", (product_id,))
    sales_count = cursor.fetchone()[0]

    # Soft delete if it has sales history, or hard delete if no history
    if sales_count > 0:
        cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        db.commit()
        return {"status": "deactivated", "message": f"Product has {sales_count} sales records. It was archived to preserve audit history.", "sales_count": sales_count}
    else:
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
        return {"status": "deleted", "message": "Product deleted successfully.", "sales_count": 0}

def list_categories() -> List[str]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category")
    return [row[0] for row in cursor.fetchall() if row[0]]

def list_suppliers() -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM suppliers ORDER BY name")
    return [dict(row) for row in cursor.fetchall()]

def create_supplier(data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("Supplier name is required")
    lead_time = max(1, int(data.get("lead_time", 7)))
    min_order_qty = max(1, int(data.get("min_order_qty", 1)))
    pack_size = max(1, int(data.get("pack_size", 1)))
    contact_email = data.get("contact_email")

    cursor.execute("""
        INSERT INTO suppliers (name, lead_time, min_order_qty, pack_size, contact_email)
        VALUES (?, ?, ?, ?, ?)
    """, (name, lead_time, min_order_qty, pack_size, contact_email))
    db.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM suppliers WHERE id = ?", (new_id,))
    return dict(cursor.fetchone())
