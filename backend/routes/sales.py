from flask import Blueprint, request, jsonify
from backend.database import get_db
from backend.services.csv_service import validate_and_preview_sales_csv, commit_sales_import

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/sales", methods=["GET"])
def get_sales():
    db = get_db()
    cursor = db.cursor()

    sku = request.args.get("sku")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    query = """
        SELECT 
            s.id,
            s.sku,
            s.sale_date,
            s.quantity_sold,
            s.import_batch_id,
            s.created_at,
            p.name as product_name,
            p.category,
            p.unit_cost,
            p.selling_price
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE 1=1
    """
    params = []

    if sku:
        query += " AND s.sku = ?"
        params.append(sku.upper())
    if start_date:
        query += " AND s.sale_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND s.sale_date <= ?"
        params.append(end_date)

    query += " ORDER BY s.sale_date DESC, s.id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    total = len(rows)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = rows[start_idx:end_idx]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
        "items": [dict(r) for r in paginated]
    }), 200

@sales_bp.route("/sales/validate", methods=["POST"])
def validate_sales_file():
    content = ""
    filename = "uploaded_sales.csv"

    if "file" in request.files:
        uploaded_file = request.files["file"]
        filename = uploaded_file.filename or filename
        content = uploaded_file.read().decode("utf-8", errors="replace")
    elif request.is_json:
        data = request.get_json()
        content = data.get("csv_content", "")
        filename = data.get("filename", filename)
    else:
        content = request.get_data(as_text=True)

    result = validate_and_preview_sales_csv(content, filename)
    return jsonify(result), 200

@sales_bp.route("/sales/import", methods=["POST"])
def import_sales_records():
    data = request.get_json()
    if not data or "valid_records" not in data:
        return jsonify({"error": "Missing valid_records array in request body"}), 400

    batch_id = data.get("batch_id", "MANUAL-IMPORT")
    filename = data.get("filename", "sales.csv")
    valid_records = data.get("valid_records", [])

    res = commit_sales_import(batch_id, filename, valid_records)
    return jsonify(res), 200
