from flask import Blueprint, request, jsonify
from backend.database import get_db
from backend.services.market_service import ingest_market_signals_csv

market_bp = Blueprint("market", __name__)

@market_bp.route("/market", methods=["GET"])
def get_market_signals():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM market_signals ORDER BY date DESC, id DESC LIMIT 100")
    return jsonify([dict(r) for r in cursor.fetchall()]), 200

@market_bp.route("/market/import", methods=["POST"])
def import_market_signals():
    content = ""
    if "file" in request.files:
        f = request.files["file"]
        content = f.read().decode("utf-8", errors="replace")
    elif request.is_json:
        data = request.get_json() or {}
        content = data.get("csv_content", "")
    else:
        content = request.get_data(as_text=True)

    res = ingest_market_signals_csv(content)
    if "error" in res:
        return jsonify(res), 400
    return jsonify(res), 200
