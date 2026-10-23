from flask import Blueprint, jsonify, Response
from backend.services.reporting_service import (
    get_ranked_reorder_report,
    get_current_inventory_report,
    get_historical_sales_report,
    get_stockout_risk_report,
    get_expiry_risk_report,
    generate_csv_stream
)

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/reports/<report_type>", methods=["GET"])
def get_report_data(report_type):
    if report_type == "reorder":
        data = get_ranked_reorder_report()
    elif report_type == "inventory":
        data = get_current_inventory_report()
    elif report_type == "sales":
        data = get_historical_sales_report()
    elif report_type == "stockout":
        data = get_stockout_risk_report()
    elif report_type == "expiry":
        data = get_expiry_risk_report()
    else:
        return jsonify({"error": f"Invalid report type '{report_type}'"}), 400

    return jsonify({
        "report_type": report_type,
        "count": len(data),
        "data": data
    }), 200

@reports_bp.route("/reports/download/<report_type>", methods=["GET"])
def download_report_csv(report_type):
    csv_content, filename = generate_csv_stream(report_type)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
