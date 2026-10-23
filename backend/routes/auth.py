from flask import Blueprint, request, jsonify
from backend.services.auth_service import authenticate_user, switch_demo_role, verify_token

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "")
    password = data.get("password", "")

    user = authenticate_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({"user": user, "message": f"Welcome back, {user['name']}!"}), 200

@auth_bp.route("/auth/switch-role", methods=["POST"])
def switch_role():
    """Allows instant role switching in demo mode."""
    data = request.get_json() or {}
    role = data.get("role", "retailer")

    user = switch_demo_role(role)
    if not user:
        return jsonify({"error": f"Role '{role}' not available."}), 404
    return jsonify({"user": user, "message": f"Switched to {role.title()} mode."}), 200

@auth_bp.route("/auth/me", methods=["GET"])
def me():
    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        token = auth_hdr[7:]
        payload = verify_token(token)
        if payload:
            return jsonify({"user": payload}), 200

    # Default to demo retailer if no token passed in demo environment
    user = switch_demo_role("retailer")
    return jsonify({"user": user}), 200
