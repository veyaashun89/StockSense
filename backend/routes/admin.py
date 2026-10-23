import os
from flask import Blueprint, request, jsonify
from backend.database import get_db, hash_password
from backend.config import Config
from backend.services.auth_service import require_roles

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin/users", methods=["GET"])
@require_roles("admin")
def list_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.id, u.email, u.role, u.name, u.shop_id, u.active, u.created_at, s.name as shop_name
        FROM users u
        LEFT JOIN shops s ON u.shop_id = s.id
        ORDER BY u.id ASC
    """)
    return jsonify([dict(r) for r in cursor.fetchall()]), 200

@admin_bp.route("/admin/users", methods=["POST"])
@require_roles("admin")
def create_user():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "retailer")
    name = data.get("name", "").strip()

    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (email, password_hash, role, name, shop_id, active)
            VALUES (?, ?, ?, ?, 1, 1)
        """, (email, hash_password(password), role, name))
        db.commit()
        return jsonify({"status": "success", "message": f"User {email} created with role {role}"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@admin_bp.route("/admin/users/<int:user_id>", methods=["PATCH"])
@require_roles("admin")
def update_user(user_id):
    data = request.get_json() or {}
    db = get_db()
    cursor = db.cursor()

    if "active" in data:
        cursor.execute("UPDATE users SET active = ? WHERE id = ?", (int(data["active"]), user_id))
    if "role" in data:
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (data["role"], user_id))

    db.commit()
    cursor.execute("SELECT id, email, role, name, active FROM users WHERE id = ?", (user_id,))
    return jsonify(dict(cursor.fetchone())), 200

@admin_bp.route("/admin/system", methods=["GET"])
@require_roles("admin")
def system_health():
    db = get_db()
    cursor = db.cursor()

    db_size = os.path.getsize(Config.DATABASE) if os.path.exists(Config.DATABASE) else 0
    cursor.execute("SELECT COUNT(*) FROM products")
    prods = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM sales")
    sales = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'OPEN'")
    alerts = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM purchase_orders")
    pos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pipeline_runs")
    pipeline = cursor.fetchone()[0]

    return jsonify({
        "status": "healthy",
        "database_file": Config.DATABASE,
        "database_size_kb": round(db_size / 1024, 1),
        "counts": {
            "products": prods,
            "sales_transactions": sales,
            "open_alerts": alerts,
            "purchase_orders": pos,
            "pipeline_runs": pipeline
        }
    }), 200
