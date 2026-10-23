from flask import Blueprint, request, jsonify
from backend.database import get_db
from backend.services.gst_service import validate_and_preview_gst_csv, commit_gst_import

gst_bp = Blueprint("gst", __name__)

@gst_bp.route("/gst/validate", methods=["POST"])
def validate_gst():
    content = ""
    filename = "gst_invoices.csv"
    if "file" in request.files:
        f = request.files["file"]
        filename = f.filename or filename
        content = f.read().decode("utf-8", errors="replace")
    elif request.is_json:
        data = request.get_json() or {}
        content = data.get("csv_content", "")
        filename = data.get("filename", filename)
    else:
        content = request.get_data(as_text=True)

    res = validate_and_preview_gst_csv(content, filename)
    return jsonify(res), 200

@gst_bp.route("/gst/import", methods=["POST"])
def import_gst():
    data = request.get_json() or {}
    batch_id = data.get("batch_id")
    filename = data.get("filename", "gst_upload.csv")
    valid_rows = data.get("valid_rows", [])
    update_stock = bool(data.get("update_stock", True))

    if not valid_rows:
        return jsonify({"error": "Missing valid_rows in payload"}), 400

    res = commit_gst_import(batch_id, filename, valid_rows, update_stock=update_stock)
    return jsonify(res), 200

@gst_bp.route("/gst/lines", methods=["GET"])
def get_gst_lines():
    db = get_db()
    cursor = db.cursor()
    supply_type = request.args.get("supply_type")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    query = "SELECT * FROM gst_lines WHERE 1=1"
    params = []
    if supply_type:
        query += " AND supply_type = ?"
        params.append(supply_type.lower())

    query += " ORDER BY invoice_date DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    total = len(rows)
    start_idx = (page - 1) * per_page
    paginated = rows[start_idx:start_idx + per_page]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [dict(r) for r in paginated]
    }), 200

@gst_bp.route("/gst/mappings", methods=["GET"])
def get_gst_mappings():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM gst_mappings ORDER BY id DESC")
    return jsonify([dict(r) for r in cursor.fetchall()]), 200

@gst_bp.route("/gst/mappings", methods=["POST"])
def add_gst_mapping():
    data = request.get_json() or {}
    hsn_code = data.get("hsn_code", "").strip()
    desc = data.get("item_description", "").strip()
    mapped_sku = data.get("mapped_sku", "").strip().upper()

    if not mapped_sku:
        return jsonify({"error": "mapped_sku is required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO gst_mappings (hsn_code, item_description, mapped_sku)
        VALUES (?, ?, ?)
    """, (hsn_code, desc, mapped_sku))
    db.commit()
    return jsonify({"status": "success", "message": f"Mapping created for SKU {mapped_sku}"}), 201
