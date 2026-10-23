from flask import Blueprint, request, jsonify
from backend.services.stock_service import ingest_stock_snapshot_csv, get_stock_batches

stock_bp = Blueprint("stock", __name__)

@stock_bp.route("/stock/batches", methods=["GET"])
def get_batches():
    prod_id = request.args.get("product_id")
    pid = int(prod_id) if prod_id and prod_id.isdigit() else None
    batches = get_stock_batches(product_id=pid)
    return jsonify(batches), 200

@stock_bp.route("/stock/import", methods=["POST"])
def import_stock_snapshot():
    content = ""
    filename = "stock_snapshot.csv"
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

    res = ingest_stock_snapshot_csv(content, filename)
    if "error" in res:
        return jsonify(res), 400
    return jsonify(res), 200
