import os
from flask import Blueprint, request, jsonify
from backend.database import get_db, init_db
from backend.config import Config
from backend.services.sample_data_service import seed_demonstration_data

data_bp = Blueprint("data", __name__)

@data_bp.route("/data/status", methods=["GET"])
def get_data_status():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
    active_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM suppliers")
    total_suppliers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sales")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(sale_date), MAX(sale_date) FROM sales")
    date_range_row = cursor.fetchone()
    min_date = date_range_row[0] if date_range_row else None
    max_date = date_range_row[1] if date_range_row else None

    cursor.execute("SELECT id, filename, total_rows, created_at FROM import_batches ORDER BY created_at DESC LIMIT 10")
    batches = [dict(r) for r in cursor.fetchall()]

    db_size_bytes = 0
    if os.path.exists(Config.DATABASE):
        db_size_bytes = os.path.getsize(Config.DATABASE)

    return jsonify({
        "database_file": Config.DATABASE,
        "database_size_kb": round(db_size_bytes / 1024, 1),
        "active_products": active_products,
        "total_suppliers": total_suppliers,
        "total_sales_records": total_sales,
        "sales_date_range": {
            "start": min_date,
            "end": max_date
        },
        "recent_import_batches": batches
    }), 200

@data_bp.route("/data/seed", methods=["POST"])
def seed_data():
    try:
        result = seed_demonstration_data(reset=True)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Failed to seed demo data: {str(e)}"}), 500

@data_bp.route("/data/reset", methods=["POST"])
def reset_data():
    data = request.get_json() or {}
    if not data.get("confirm"):
        return jsonify({"error": "Reset confirmation required. Pass {'confirm': true}"}), 400

    try:
        init_db(drop_all=True)
        return jsonify({"status": "success", "message": "All database tables have been reset to empty state."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to reset database: {str(e)}"}), 500
