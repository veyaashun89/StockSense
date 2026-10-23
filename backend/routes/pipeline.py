from flask import Blueprint, jsonify, request
from backend.services.pipeline_service import run_pipeline, get_latest_pipeline_status, list_pipeline_runs

pipeline_bp = Blueprint("pipeline", __name__)

@pipeline_bp.route("/pipeline/status", methods=["GET"])
def pipeline_status():
    status = get_latest_pipeline_status()
    return jsonify(status), 200

@pipeline_bp.route("/pipeline/runs", methods=["GET"])
def pipeline_runs():
    limit = int(request.args.get("limit", 20))
    runs = list_pipeline_runs(limit=limit)
    return jsonify({"total": len(runs), "runs": runs}), 200

@pipeline_bp.route("/pipeline/run", methods=["POST"])
def trigger_pipeline():
    res = run_pipeline(triggered_by="MANUAL_UI")
    return jsonify(res), 200
