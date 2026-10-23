from flask import Blueprint, request, jsonify
from backend.database import get_db

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT key, value, description FROM settings")
    settings_dict = {row["key"]: row["value"] for row in cursor.fetchall()}
    return jsonify(settings_dict), 200

@settings_bp.route("/settings", methods=["PUT"])
def update_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body missing"}), 400

    db = get_db()
    cursor = db.cursor()

    allowed_keys = {
        "lead_time_days", "safety_buffer_days", "coverage_days",
        "historical_window_days", "forecast_horizon_days",
        "currency", "budget", "forecast_method"
    }

    for key, value in data.items():
        if key in allowed_keys:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))

    db.commit()

    cursor.execute("SELECT key, value FROM settings")
    updated = {row["key"]: row["value"] for row in cursor.fetchall()}
    return jsonify({"status": "success", "settings": updated}), 200
