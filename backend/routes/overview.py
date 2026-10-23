from flask import Blueprint, jsonify, request
from backend.services.auth_service import require_roles, get_current_user_context
from backend.services.overview_service import (
    get_retailer_overview,
    get_wholesaler_overview,
    get_dealer_overview,
    get_admin_overview,
    invalidate_overview_cache
)

overview_bp = Blueprint("overview", __name__)

@overview_bp.route("/overview", methods=["GET"])
def get_unified_overview():
    """
    Returns role-scoped overview based on authenticated user context.
    The server decides what each role may see.
    """
    user = get_current_user_context(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    role = user.get("role", "retailer").lower()
    if role == "wholesaler":
        return jsonify(get_wholesaler_overview(user.get("user_id", 1))), 200
    elif role == "dealer":
        return jsonify(get_dealer_overview(user.get("user_id", 1))), 200
    elif role == "admin":
        return jsonify(get_admin_overview()), 200
    else:
        return jsonify(get_retailer_overview(user.get("shop_id", 1))), 200

@overview_bp.route("/overview/retailer", methods=["GET"])
@require_roles("retailer")
def get_retailer_route():
    user = get_current_user_context(request)
    shop_id = user.get("shop_id", 1) if user else 1
    data = get_retailer_overview(shop_id=shop_id)
    return jsonify(data), 200

@overview_bp.route("/overview/wholesaler", methods=["GET"])
@require_roles("wholesaler")
def get_wholesaler_route():
    user = get_current_user_context(request)
    wholesaler_id = user.get("user_id", 1) if user else 1
    data = get_wholesaler_overview(wholesaler_id=wholesaler_id)
    return jsonify(data), 200

@overview_bp.route("/overview/dealer", methods=["GET"])
@require_roles("dealer")
def get_dealer_route():
    user = get_current_user_context(request)
    dealer_id = user.get("user_id", 1) if user else 1
    data = get_dealer_overview(dealer_id=dealer_id)
    return jsonify(data), 200

@overview_bp.route("/overview/admin", methods=["GET"])
@require_roles("admin")
def get_admin_route():
    data = get_admin_overview()
    return jsonify(data), 200

@overview_bp.route("/overview/cache/invalidate", methods=["POST"])
@require_roles("admin")
def invalidate_cache_route():
    invalidate_overview_cache()
    return jsonify({"status": "invalidated", "message": "Overview cache cleared"}), 200
