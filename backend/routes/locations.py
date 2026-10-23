from flask import Blueprint, request, jsonify
from backend.repositories.location_repository import LocationRepository
from backend.services.location_service import process_box_scan, seed_demo_locations
from backend.services.auth_service import require_roles

locations_bp = Blueprint("locations", __name__)

@locations_bp.route("/locations", methods=["GET"])
@require_roles("retailer", "wholesaler", "admin")
def get_locations():
    """List all physical storage locations (shelves, bins, boxes) with stock and parent hierarchy."""
    seed_demo_locations()
    locations = LocationRepository.list_locations()
    return jsonify({"locations": locations, "total": len(locations)}), 200

@locations_bp.route("/locations", methods=["POST"])
@require_roles("wholesaler", "admin")
def create_location():
    """Create a new location in the warehouse or store hierarchy."""
    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "Location name is required"}), 400

    loc = LocationRepository.create_location(
        name=name,
        location_type=data.get("location_type", "shelf"),
        barcode=data.get("barcode"),
        parent_id=data.get("parent_id"),
        description=data.get("description")
    )
    return jsonify({"status": "success", "location": loc}), 201

@locations_bp.route("/locations/<int:location_id>", methods=["GET"])
@require_roles("retailer", "wholesaler", "admin")
def get_single_location(location_id: int):
    """Retrieve details and stock items for a single location."""
    loc = LocationRepository.get_location(location_id)
    if not loc:
        return jsonify({"error": "Location not found"}), 404
    return jsonify({"location": loc}), 200

@locations_bp.route("/locations/<int:location_id>/stock", methods=["POST"])
@require_roles("wholesaler", "admin")
def set_stock(location_id: int):
    """Set or update expected stock quantity for a specific SKU in a location."""
    data = request.get_json() or {}
    sku = data.get("sku")
    expected_qty = data.get("expected_quantity")

    if not sku or expected_qty is None:
        return jsonify({"error": "sku and expected_quantity are required"}), 400

    try:
        updated = LocationRepository.set_location_stock(location_id, sku, int(expected_qty))
        return jsonify({"status": "success", "stock": updated}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@locations_bp.route("/locations/<int:location_id>/box-scan", methods=["POST"])
@require_roles("wholesaler", "retailer", "admin")
def box_scan(location_id: int):
    """
    Box Scan & Reconciliation Flow:
    Accepts webcam frame or image data of a box / bin, runs barcode decode + CV matching,
    counts each item once, reconciles with expected stock, and raises mismatch alerts.
    """
    data = request.get_json() or {}
    image_data = data.get("image_data")

    # If direct scanned counts passed without camera frame
    scanned_counts = data.get("scanned_counts")
    if scanned_counts and isinstance(scanned_counts, dict):
        reconciliation = LocationRepository.reconcile_box_counts(location_id, scanned_counts)
        return jsonify({"status": "success", "reconciliation": reconciliation}), 200

    if not image_data and "file" in request.files:
        import base64
        image_data = base64.b64encode(request.files["file"].read()).decode("utf-8")

    if not image_data:
        return jsonify({"error": "image_data (base64) or scanned_counts dictionary is required"}), 400

    try:
        result = process_box_scan(location_id, image_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
