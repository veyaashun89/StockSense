from flask import Blueprint, request, jsonify
from backend.services.alert_service import list_alerts, update_alert_status, evaluate_and_generate_alerts

alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/alerts", methods=["GET"])
def get_alerts():
    status = request.args.get("status")
    severity = request.args.get("severity")
    items = list_alerts(status=status, severity=severity)
    open_count = sum(1 for a in items if a["status"] == "OPEN")
    critical_count = sum(1 for a in items if a["status"] == "OPEN" and a["severity"] == "CRITICAL")
    return jsonify({
        "total": len(items),
        "open_count": open_count,
        "critical_count": critical_count,
        "items": items
    }), 200

@alerts_bp.route("/alerts/<int:alert_id>", methods=["PATCH"])
def patch_alert(alert_id):
    data = request.get_json() or {}
    new_status = data.get("status", "ACKNOWLEDGED")
    try:
        updated = update_alert_status(alert_id, new_status)
        if not updated:
            return jsonify({"error": "Alert not found"}), 404
        return jsonify(updated), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@alerts_bp.route("/alerts/evaluate", methods=["POST"])
def run_alert_evaluation():
    res = evaluate_and_generate_alerts()
    return jsonify(res), 200
