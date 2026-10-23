import base64
from flask import Blueprint, request, jsonify
from backend.services.import_service import (
    process_sales_import,
    process_stock_import,
    get_past_sales_records,
    get_stock_movements_history,
    get_import_batches_list
)
from backend.services.auth_service import require_roles

records_bp = Blueprint("records_api", __name__)

@records_bp.route("/records/import/sales", methods=["POST"])
@require_roles("retailer", "wholesaler", "admin")
def import_sales():
    """Import past sales from CSV or Excel file, with optional ?dry_run=true."""
    dry_run = request.args.get("dry_run", "false").lower() in ("true", "1")
    filename = "sales_import.csv"
    file_bytes = None

    if "file" in request.files:
        f = request.files["file"]
        filename = f.filename or filename
        file_bytes = f.read()
    else:
        data = request.get_json() or {}
        content_b64 = data.get("content_base64")
        filename = data.get("filename", filename)
        dry_run = data.get("dry_run", dry_run)
        if content_b64:
            file_bytes = base64.b64decode(content_b64)
        elif "content" in data:
            file_bytes = data["content"].encode("utf-8")

    if not file_bytes:
        return jsonify({"error": "No file uploaded or content provided"}), 400

    result = process_sales_import(file_bytes, filename, dry_run=dry_run)
    return jsonify(result), 200

@records_bp.route("/records/import/stock", methods=["POST"])
@require_roles("wholesaler", "admin")
def import_stock():
    """Import stock snapshot from CSV or Excel file, with optional ?dry_run=true."""
    dry_run = request.args.get("dry_run", "false").lower() in ("true", "1")
    filename = "stock_import.csv"
    file_bytes = None

    if "file" in request.files:
        f = request.files["file"]
        filename = f.filename or filename
        file_bytes = f.read()
    else:
        data = request.get_json() or {}
        content_b64 = data.get("content_base64")
        filename = data.get("filename", filename)
        dry_run = data.get("dry_run", dry_run)
        if content_b64:
            file_bytes = base64.b64decode(content_b64)
        elif "content" in data:
            file_bytes = data["content"].encode("utf-8")

    if not file_bytes:
        return jsonify({"error": "No file uploaded or content provided"}), 400

    result = process_stock_import(file_bytes, filename, dry_run=dry_run)
    return jsonify(result), 200

@records_bp.route("/records/sales", methods=["GET"])
def get_sales():
    """Query past sales records aggregated by day or week."""
    group_by = request.args.get("group_by", "day")
    sku = request.args.get("sku")
    limit = int(request.args.get("limit", 100))

    records = get_past_sales_records(group_by=group_by, sku=sku, limit=limit)
    return jsonify({"sales": records, "count": len(records), "group_by": group_by}), 200

@records_bp.route("/records/stock-movements", methods=["GET"])
def get_movements():
    """Query full inventory movement history for auditing."""
    sku = request.args.get("sku")
    limit = int(request.args.get("limit", 100))

    movements = get_stock_movements_history(sku=sku, limit=limit)
    return jsonify({"movements": movements, "count": len(movements)}), 200

@records_bp.route("/records/batches", methods=["GET"])
def get_batches():
    """Query import batches for auditing past data loads."""
    batches = get_import_batches_list()
    return jsonify({"batches": batches, "count": len(batches)}), 200
