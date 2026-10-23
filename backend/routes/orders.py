from flask import Blueprint, request, jsonify
from backend.services.order_service import (
    list_purchase_orders, get_purchase_order, create_purchase_order, update_purchase_order_status
)
from backend.services.auth_service import require_roles

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/orders", methods=["GET"])
@require_roles("retailer", "wholesaler", "admin")
def get_orders():
    status = request.args.get("status")
    wholesaler_id = request.args.get("wholesaler_id")
    wid = int(wholesaler_id) if wholesaler_id and wholesaler_id.isdigit() else None

    orders = list_purchase_orders(status=status, wholesaler_id=wid)
    return jsonify({"total": len(orders), "items": orders}), 200

@orders_bp.route("/orders", methods=["POST"])
@require_roles("retailer", "wholesaler", "admin")
def place_order():
    data = request.get_json() or {}
    items = data.get("items", [])
    wholesaler_id = data.get("wholesaler_id")
    notes = data.get("notes")

    if not items:
        return jsonify({"error": "No items provided in order"}), 400

    try:
        po = create_purchase_order(items=items, wholesaler_id=wholesaler_id, notes=notes)
        return jsonify(po), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@orders_bp.route("/orders/<int:po_id>", methods=["GET"])
@require_roles("retailer", "wholesaler", "admin")
def get_order_detail(po_id):
    po = get_purchase_order(po_id)
    if not po:
        return jsonify({"error": "Purchase order not found"}), 404
    return jsonify(po), 200

@orders_bp.route("/orders/<int:po_id>/status", methods=["PATCH"])
@require_roles("wholesaler", "admin")
def change_order_status(po_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    received_qtys = data.get("received_quantities")

    if not new_status:
        return jsonify({"error": "status is required"}), 400

    try:
        po = update_purchase_order_status(po_id, new_status, received_quantities=received_qtys)
        return jsonify(po), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
