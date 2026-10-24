from flask import Blueprint, jsonify, request
from backend.services.analysis_service import compute_demo_analytics, compute_live_analytics

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/analytics/demo", methods=["GET"])
def get_demo_analytics_route():
    """Returns analytics computed dynamically from backend/demo_data/*.csv."""
    data = compute_demo_analytics()
    return jsonify(data), 200

@analytics_bp.route("/analytics/demo/import", methods=["POST"])
def import_demo_analytics_route():
    """Triggers re-import and recalculation from backend/demo_data/*.csv."""
    data = compute_demo_analytics()
    return jsonify({
        "status": "success",
        "message": f"Successfully loaded and recomputed analytics from {len(data['source_files'])} CSV files.",
        "data": data
    }), 200

@analytics_bp.route("/analytics/live", methods=["GET"])
def get_live_analytics_route():
    """Returns live analytics strictly from the SQLite database with real timestamps."""
    data = compute_live_analytics()
    return jsonify(data), 200
