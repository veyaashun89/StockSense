from flask import Blueprint, request, jsonify
from backend.services.reorder_service import generate_reorder_plan

reorder_bp = Blueprint("reorder", __name__)

@reorder_bp.route("/reorder", methods=["GET"])
def get_reorder_plan():
    category = request.args.get("category")
    priority_filter = request.args.get("priority")
    search = request.args.get("search")
    budget_raw = request.args.get("budget")
    budget = float(budget_raw) if budget_raw is not None and budget_raw != "" else None

    try:
        plan = generate_reorder_plan(
            category=category,
            priority_filter=priority_filter,
            search=search,
            budget_limit=budget
        )
        return jsonify(plan), 200
    except Exception as e:
        return jsonify({"error": f"Failed to generate reorder plan: {str(e)}"}), 500

@reorder_bp.route("/reorder/run", methods=["POST"])
def run_reorder_plan():
    data = request.get_json() or {}
    category = data.get("category")
    priority_filter = data.get("priority")
    search = data.get("search")
    budget = float(data["budget"]) if data.get("budget") is not None and str(data["budget"]).strip() != "" else None

    try:
        plan = generate_reorder_plan(
            category=category,
            priority_filter=priority_filter,
            search=search,
            budget_limit=budget
        )
        return jsonify(plan), 200
    except Exception as e:
        return jsonify({"error": f"Failed to recalculate reorder plan: {str(e)}"}), 500
