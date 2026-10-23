from flask import Blueprint, request, jsonify
from backend.database import get_db
from backend.services.forecasting_service import forecast_demand, forecast_demand_weekly

forecast_bp = Blueprint("forecast", __name__)

@forecast_bp.route("/forecast/weekly", methods=["GET"])
def get_weekly_forecast():
    db = get_db()
    cursor = db.cursor()

    product_id = request.args.get("product_id")
    sku = request.args.get("sku")
    horizon_weeks = int(request.args.get("horizon_weeks", 4))
    window_days = int(request.args.get("window", 60))

    if not product_id and not sku:
        cursor.execute("SELECT id FROM products WHERE is_active = 1 ORDER BY id ASC LIMIT 1")
        first = cursor.fetchone()
        if not first:
            return jsonify({"error": "No products available"}), 404
        product_id = first["id"]
    elif sku and not product_id:
        cursor.execute("SELECT id FROM products WHERE sku = ?", (sku.upper(),))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": f"Product '{sku}' not found"}), 404
        product_id = row["id"]

    try:
        res = forecast_demand_weekly(int(product_id), horizon_weeks=horizon_weeks, window_days=window_days)
        return jsonify(res), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Weekly forecast failed: {str(e)}"}), 500

@forecast_bp.route("/forecast", methods=["GET"])
def get_forecast():
    db = get_db()
    cursor = db.cursor()

    product_id = request.args.get("product_id")
    sku = request.args.get("sku")
    horizon = int(request.args.get("horizon", 14))
    window = int(request.args.get("window", 30))
    method = request.args.get("method", "moving_average")

    if not product_id and not sku:
        # Default to first active product
        cursor.execute("SELECT id FROM products WHERE is_active = 1 ORDER BY id ASC LIMIT 1")
        first = cursor.fetchone()
        if not first:
            return jsonify({"error": "No products available in database"}), 404
        product_id = first["id"]
    elif sku and not product_id:
        cursor.execute("SELECT id FROM products WHERE sku = ?", (sku.upper(),))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": f"Product with SKU '{sku}' not found"}), 404
        product_id = row["id"]

    try:
        result = forecast_demand(
            int(product_id),
            horizon_days=horizon,
            window_days=window,
            method=method
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Forecast calculation failed: {str(e)}"}), 500

@forecast_bp.route("/forecast/run", methods=["POST"])
def run_forecast():
    data = request.get_json() or {}
    product_id = data.get("product_id")
    horizon = int(data.get("horizon", 14))
    window = int(data.get("window", 30))
    method = data.get("method", "moving_average")

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    try:
        result = forecast_demand(
            int(product_id),
            horizon_days=horizon,
            window_days=window,
            method=method
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Forecast calculation failed: {str(e)}"}), 500
