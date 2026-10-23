from flask import Blueprint, request, jsonify
from backend.database import get_db
from backend.services.auth_service import require_roles

wholesale_bp = Blueprint("wholesale", __name__)

@wholesale_bp.route("/wholesale/catalog", methods=["GET"])
def get_catalog():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.*, u.name as wholesaler_name
        FROM wholesale_catalog_items c
        JOIN users u ON c.wholesaler_id = u.id
        ORDER BY c.category, c.name
    """)
    return jsonify([dict(r) for r in cursor.fetchall()]), 200

@wholesale_bp.route("/wholesale/catalog", methods=["POST"])
@require_roles("wholesaler", "admin")
def add_catalog_item():
    data = request.get_json() or {}
    wholesaler_id = int(data.get("wholesaler_id", 2)) # Default demo wholesaler ID
    sku = data.get("sku", "").strip().upper()
    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    price = float(data.get("wholesale_price", 0))
    moq = int(data.get("moq", 10))
    pack_size = int(data.get("pack_size", 5))
    lead = int(data.get("lead_time_days", 3))
    shelf = int(data["shelf_life_days"]) if data.get("shelf_life_days") else None
    stock = int(data.get("available_stock", 500))

    if not sku or not name:
        return jsonify({"error": "SKU and Name are required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO wholesale_catalog_items (
            wholesaler_id, sku, name, category, wholesale_price,
            moq, pack_size, lead_time_days, shelf_life_days, available_stock
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (wholesaler_id, sku, name, category, price, moq, pack_size, lead, shelf, stock))
    db.commit()
    return jsonify({"status": "success", "message": f"Added {name} ({sku}) to wholesale catalog"}), 201

@wholesale_bp.route("/wholesale/demand-signals", methods=["GET"])
def get_demand_signals():
    """Aggregated, anonymized weekly demand signals across products to help wholesalers plan upstream supply."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            p.sku,
            p.name as product_name,
            p.category,
            ROUND(AVG(s.quantity_sold), 1) as avg_daily_store_demand,
            ROUND(AVG(s.quantity_sold) * 7, 0) as projected_weekly_demand,
            COUNT(DISTINCT s.product_id) as ordering_stores_count
        FROM products p
        LEFT JOIN sales s ON p.id = s.product_id
        WHERE p.is_active = 1
        GROUP BY p.sku
        ORDER BY projected_weekly_demand DESC
    """)
    return jsonify([dict(r) for r in cursor.fetchall()]), 200
