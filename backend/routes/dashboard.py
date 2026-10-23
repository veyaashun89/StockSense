import datetime
from flask import Blueprint, jsonify, request
from backend.database import get_db
from backend.services.reorder_service import generate_reorder_plan
from backend.services.auth_service import get_current_user_context

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard_data():
    current_user = get_current_user_context(request)
    role = current_user.get("role", "retailer").lower()

    db = get_db()
    cursor = db.cursor()

    # 1. Wholesaler Dashboard View
    if role == "wholesaler":
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(available_stock), 0) FROM wholesale_catalog_items")
        cat_count, total_wh_stock = cursor.fetchone()

        cursor.execute("""
            SELECT status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total_val
            FROM purchase_orders
            GROUP BY status
        """)
        po_status_map = {row["status"]: {"count": row["count"], "value": row["total_val"]} for row in cursor.fetchall()}

        cursor.execute("""
            SELECT po_number, status, total_amount, created_at, buyer_id
            FROM purchase_orders
            ORDER BY created_at DESC LIMIT 5
        """)
        recent_pos = [dict(r) for r in cursor.fetchall()]

        return jsonify({
            "role": "wholesaler",
            "last_updated": datetime.datetime.now().isoformat(),
            "summary": {
                "catalog_items": cat_count,
                "total_available_stock": total_wh_stock,
                "pending_fulfillment": po_status_map.get("SUBMITTED", {}).get("count", 0),
                "in_transit": po_status_map.get("DISPATCHED", {}).get("count", 0),
                "delivered": po_status_map.get("DELIVERED", {}).get("count", 0)
            },
            "order_pipeline": po_status_map,
            "recent_orders": recent_pos,
            "demand_signal": "HIGH (Aggregated Retail Demand +14% vs last week)"
        }), 200

    # 2. Dealer Dashboard View
    if role == "dealer":
        # Dealer specific metrics: Regional dealership margin, distribution quotas, regional stock
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(current_stock), 0) FROM products WHERE is_active = 1")
        prod_count, store_stock = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM purchase_orders WHERE status IN ('SUBMITTED', 'CONFIRMED')")
        active_allocations = cursor.fetchone()[0]

        dealer_margins = [
            {"tier": "Tier 1: Staples & Grains", "margin": "8.5%", "status": "OPTIMAL"},
            {"tier": "Tier 2: Packaged Foods", "margin": "12.0%", "status": "HIGH_DEMAND"},
            {"tier": "Tier 3: Dairy & Perishables", "margin": "14.5%", "status": "RAPID_TURNOVER"}
        ]

        return jsonify({
            "role": "dealer",
            "last_updated": datetime.datetime.now().isoformat(),
            "dealership_name": "Metro Regional Dealers Hub (Territory #4)",
            "summary": {
                "active_skus": prod_count,
                "regional_stock_allocated": store_stock,
                "open_dealer_allocations": active_allocations,
                "average_dealer_margin": "11.7%"
            },
            "margin_tiers": dealer_margins,
            "dealer_territory": "North-West Metropolitan District"
        }), 200

    # 3. Admin Dashboard View
    if role == "admin":
        cursor.execute("SELECT COUNT(*) FROM users WHERE active = 1")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pipeline_runs")
        pipeline_run_count = cursor.fetchone()[0]

        cursor.execute("SELECT id, action, entity, actor_id, at FROM audit_log ORDER BY at DESC LIMIT 5")
        recent_audits = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'OPEN'")
        open_alerts_count = cursor.fetchone()[0]

        return jsonify({
            "role": "admin",
            "last_updated": datetime.datetime.now().isoformat(),
            "summary": {
                "active_users": user_count,
                "total_pipeline_runs": pipeline_run_count,
                "open_system_alerts": open_alerts_count,
                "system_status": "OPERATIONAL"
            },
            "recent_audit_logs": recent_audits,
            "engine_info": {"sqlite_wal": True, "yolo_model": "yolov8n_custom.onnx"}
        }), 200

    # 4. Retailer Dashboard View (Default)
    plan = generate_reorder_plan()
    summary = plan["summary"]
    items = plan["items"]

    cursor.execute("""
        SELECT sale_date, SUM(quantity_sold) as total_units
        FROM sales
        GROUP BY sale_date
        ORDER BY sale_date DESC
        LIMIT 14
    """)
    hist_rows = cursor.fetchall()
    hist_rows.reverse()
    
    historical_chart = [
        {"date": row["sale_date"], "actual_sales": row["total_units"]}
        for row in hist_rows
    ]

    avg_store_daily = sum(x["actual_sales"] for x in historical_chart) / len(historical_chart) if historical_chart else 0.0

    last_hist_date_str = historical_chart[-1]["date"] if historical_chart else datetime.date.today().isoformat()
    try:
        last_date = datetime.date.fromisoformat(last_hist_date_str)
    except Exception:
        last_date = datetime.date.today()
    
    trend_series = []
    for h in historical_chart:
        trend_series.append({
            "date": h["date"],
            "actual_sales": h["actual_sales"],
            "forecast_demand": None
        })

    if trend_series:
        trend_series[-1]["forecast_demand"] = trend_series[-1]["actual_sales"]

    for i in range(1, 8):
        future_dt = last_date + datetime.timedelta(days=i)
        pred = round(avg_store_daily * (1.1 if future_dt.weekday() in (5, 6) else 0.98), 1)
        trend_series.append({
            "date": future_dt.isoformat(),
            "actual_sales": None,
            "forecast_demand": pred
        })

    health_distribution = [
        {"name": "Healthy", "count": summary["healthy_count"], "color": "#15803D"},
        {"name": "Reorder Required", "count": summary["medium_urgency"], "color": "#D97706"},
        {"name": "High Urgency", "count": summary["high_urgency"], "color": "#EA580C"},
        {"name": "Critical Stockout", "count": summary["critical_stockouts"], "color": "#DC2626"},
    ]

    top_urgent = [it for it in items if it["priority"] in ("CRITICAL", "HIGH")][:7]
    if not top_urgent:
        top_urgent = items[:7]

    return jsonify({
        "role": "retailer",
        "last_updated": datetime.datetime.now().isoformat(),
        "summary": summary,
        "trend_chart": trend_series,
        "health_distribution": health_distribution,
        "top_urgent_products": top_urgent
    }), 200

