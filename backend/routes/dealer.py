import datetime
from flask import Blueprint, request, jsonify
from backend.services.auth_service import require_roles
from backend.database import get_db

dealer_bp = Blueprint("dealer", __name__)

# In-memory mock storage for dealer dispatches and pricing tiers if table not yet migrated
_DEALER_DISPATCHES = [
    {
        "id": 1,
        "brand": "Amul Dairy Corp",
        "sku": "SKU-MILK-001",
        "product_name": "Amul Taaza Milk 500ml",
        "units": 500,
        "region": "Maharashtra-Zone-1",
        "status": "IN_TRANSIT",
        "carrier": "BlueDart Express Logistics",
        "tracking_code": "BD-MH-849201",
        "dispatch_date": "2026-10-23"
    },
    {
        "id": 2,
        "brand": "Britannia Industries",
        "sku": "SKU-BREAD-002",
        "product_name": "Britannia Whole Wheat Bread",
        "units": 350,
        "region": "Karnataka-South-2",
        "status": "DISPATCHED",
        "carrier": "Delhivery Freight",
        "tracking_code": "DL-KA-302194",
        "dispatch_date": "2026-10-24"
    }
]

_PRICING_TIERS = [
    {"id": 1, "tier_name": "Tier 1: Standard Retailer", "min_units": 10, "discount_pct": 5.0, "credit_days": 7},
    {"id": 2, "tier_name": "Tier 2: Wholesale Hub", "min_units": 100, "discount_pct": 14.5, "credit_days": 21},
    {"id": 3, "tier_name": "Tier 3: Mega Superstockist", "min_units": 500, "discount_pct": 22.0, "credit_days": 45}
]

_REGIONAL_ALLOCATIONS = [
    {"region": "North (Delhi NCR)", "warehouse_hub": "Gurugram Logistics Center", "allocated_crates": 450, "utilization_pct": 82.5},
    {"region": "West (Maharashtra / Gujarat)", "warehouse_hub": "Bhiwandi Central Facility", "allocated_crates": 720, "utilization_pct": 91.0},
    {"region": "South (Karnataka / TN)", "warehouse_hub": "Peenya Hub Bengaluru", "allocated_crates": 250, "utilization_pct": 68.4}
]

@dealer_bp.route("/dealer/dispatches", methods=["GET"])
@require_roles("dealer", "admin")
def list_dispatches():
    """List brand-level order dispatches and transit statuses."""
    return jsonify({
        "status": "success",
        "dispatches": _DEALER_DISPATCHES,
        "count": len(_DEALER_DISPATCHES)
    }), 200

@dealer_bp.route("/dealer/dispatches", methods=["POST"])
@require_roles("dealer", "admin")
def create_dispatch():
    """Create a brand-level dispatch order to a regional hub."""
    data = request.get_json() or {}
    brand = data.get("brand", "StockSense Direct")
    sku = data.get("sku")
    units = int(data.get("units", 100))
    region = data.get("region", "National-Central")

    if not sku:
        return jsonify({"error": "SKU is required"}), 400

    new_dispatch = {
        "id": len(_DEALER_DISPATCHES) + 1,
        "brand": brand,
        "sku": sku,
        "product_name": data.get("product_name", sku),
        "units": units,
        "region": region,
        "status": "SCHEDULED",
        "carrier": data.get("carrier", "National Freight Express"),
        "tracking_code": f"DSP-{datetime.date.today().strftime('%m%d')}-{len(_DEALER_DISPATCHES) + 1:03d}",
        "dispatch_date": datetime.date.today().isoformat()
    }
    _DEALER_DISPATCHES.append(new_dispatch)
    return jsonify({"status": "success", "dispatch": new_dispatch}), 201

@dealer_bp.route("/dealer/pricing-tiers", methods=["GET"])
@require_roles("dealer", "admin")
def get_pricing_tiers():
    """Retrieve volume discount pricing tiers for regional distributors."""
    return jsonify({
        "status": "success",
        "tiers": _PRICING_TIERS,
        "count": len(_PRICING_TIERS)
    }), 200

@dealer_bp.route("/dealer/pricing-tiers", methods=["POST"])
@require_roles("dealer", "admin")
def set_pricing_tier():
    """Configure or add a bulk pricing tier."""
    data = request.get_json() or {}
    tier_name = data.get("tier_name")
    min_units = int(data.get("min_units", 50))
    discount_pct = float(data.get("discount_pct", 10.0))
    credit_days = int(data.get("credit_days", 14))

    if not tier_name:
        return jsonify({"error": "tier_name is required"}), 400

    new_tier = {
        "id": len(_PRICING_TIERS) + 1,
        "tier_name": tier_name,
        "min_units": min_units,
        "discount_pct": discount_pct,
        "credit_days": credit_days
    }
    _PRICING_TIERS.append(new_tier)
    return jsonify({"status": "success", "tier": new_tier}), 201

@dealer_bp.route("/dealer/allocations", methods=["GET"])
@require_roles("dealer", "admin")
def get_allocations():
    """Retrieve regional inventory allocations."""
    return jsonify({
        "status": "success",
        "allocations": _REGIONAL_ALLOCATIONS,
        "total_regions": len(_REGIONAL_ALLOCATIONS)
    }), 200

@dealer_bp.route("/dealer/allocations", methods=["POST"])
@require_roles("dealer", "admin")
def update_allocation():
    """Update or allocate regional inventory."""
    data = request.get_json() or {}
    region = data.get("region")
    allocated = int(data.get("allocated_crates", 100))
    hub = data.get("warehouse_hub", "Regional Central Hub")

    if not region:
        return jsonify({"error": "region is required"}), 400

    found = False
    for item in _REGIONAL_ALLOCATIONS:
        if item["region"].lower() == region.lower():
            item["allocated_crates"] = allocated
            item["warehouse_hub"] = hub
            found = True
            break
    
    if not found:
        _REGIONAL_ALLOCATIONS.append({
            "region": region,
            "warehouse_hub": hub,
            "allocated_crates": allocated,
            "utilization_pct": 50.0
        })

    return jsonify({"status": "success", "message": f"Allocated {allocated} crates to {region}"}), 200
