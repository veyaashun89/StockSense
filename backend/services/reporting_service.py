import io
import csv
import datetime
from typing import Dict, Any, List
from backend.database import get_db
from backend.services.reorder_service import generate_reorder_plan

def get_ranked_reorder_report() -> List[Dict[str, Any]]:
    plan = generate_reorder_plan()
    return plan["items"]

def get_current_inventory_report() -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            p.sku,
            p.name,
            p.category,
            p.current_stock,
            p.unit_cost,
            p.selling_price,
            ROUND(p.current_stock * p.unit_cost, 2) as inventory_value,
            p.lead_time_days,
            p.is_perishable,
            p.shelf_life_days,
            s.name as supplier_name
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.is_active = 1
        ORDER BY p.category, p.name
    """)
    return [dict(r) for r in cursor.fetchall()]

def get_historical_sales_report(days: int = 30) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            s.sale_date,
            s.sku,
            p.name as product_name,
            p.category,
            s.quantity_sold,
            p.unit_cost,
            p.selling_price,
            ROUND(s.quantity_sold * p.selling_price, 2) as total_revenue
        FROM sales s
        JOIN products p ON s.product_id = p.id
        ORDER BY s.sale_date DESC, s.sku ASC
        LIMIT 500
    """)
    return [dict(r) for r in cursor.fetchall()]

def get_stockout_risk_report() -> List[Dict[str, Any]]:
    plan = generate_reorder_plan()
    risks = [item for item in plan["items"] if item["priority"] in ("CRITICAL", "HIGH")]
    return risks

def get_expiry_risk_report() -> List[Dict[str, Any]]:
    plan = generate_reorder_plan()
    risks = [item for item in plan["items"] if item["is_perishable"] and (item["expiry_risk"] or item.get("shelf_life_capped"))]
    return risks

def generate_csv_stream(report_type: str) -> Tuple[str, str]:
    """
    Returns (csv_string, filename) for download.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "reorder":
        filename = f"stocksense_reorder_plan_{timestamp}.csv"
        items = get_ranked_reorder_report()
        writer.writerow([
            "Priority", "SKU", "Product Name", "Category", "Current Stock",
            "Avg Daily Demand", "Lead Time Days", "Lead Time Demand", "Safety Stock",
            "Reorder Point", "Target Stock", "Recommended Qty", "Unit Cost", "Purchase Cost",
            "Shelf Life Days", "Primary Reason"
        ])
        for it in items:
            writer.writerow([
                it["priority"], it["sku"], it["name"], it["category"], it["current_stock"],
                it["average_daily_demand"], it["lead_time_days"], it["lead_time_demand"],
                it["safety_stock"], it["reorder_point"], it["target_stock"],
                it["recommended_reorder_qty"], it["unit_cost"], it["purchase_cost"],
                it["shelf_life_days"] or "N/A", it["recommendation_reason"]
            ])

    elif report_type == "inventory":
        filename = f"stocksense_inventory_status_{timestamp}.csv"
        items = get_current_inventory_report()
        writer.writerow([
            "SKU", "Product Name", "Category", "Current Stock", "Unit Cost",
            "Selling Price", "Inventory Value", "Lead Time Days", "Is Perishable",
            "Shelf Life Days", "Supplier"
        ])
        for it in items:
            writer.writerow([
                it["sku"], it["name"], it["category"], it["current_stock"], it["unit_cost"],
                it["selling_price"], it["inventory_value"], it["lead_time_days"],
                "Yes" if it["is_perishable"] else "No", it["shelf_life_days"] or "N/A",
                it["supplier_name"] or "N/A"
            ])

    elif report_type == "sales":
        filename = f"stocksense_sales_history_{timestamp}.csv"
        items = get_historical_sales_report()
        writer.writerow([
            "Sale Date", "SKU", "Product Name", "Category", "Quantity Sold",
            "Unit Cost", "Selling Price", "Total Revenue"
        ])
        for it in items:
            writer.writerow([
                it["sale_date"], it["sku"], it["product_name"], it["category"],
                it["quantity_sold"], it["unit_cost"], it["selling_price"], it["total_revenue"]
            ])

    elif report_type == "stockout":
        filename = f"stocksense_stockout_risks_{timestamp}.csv"
        items = get_stockout_risk_report()
        writer.writerow([
            "Priority", "SKU", "Product Name", "Category", "Current Stock",
            "Avg Daily Demand", "Days Until Stockout", "Lead Time Days", "Recommended Qty", "Action Reason"
        ])
        for it in items:
            writer.writerow([
                it["priority"], it["sku"], it["name"], it["category"], it["current_stock"],
                it["average_daily_demand"], it["days_until_stockout"], it["lead_time_days"],
                it["recommended_reorder_qty"], it["recommendation_reason"]
            ])

    elif report_type == "expiry":
        filename = f"stocksense_expiry_risks_{timestamp}.csv"
        items = get_expiry_risk_report()
        writer.writerow([
            "SKU", "Product Name", "Category", "Current Stock", "Shelf Life Days",
            "Avg Daily Demand", "Usable Life Days", "Recommended Qty", "Shelf Life Note"
        ])
        for it in items:
            writer.writerow([
                it["sku"], it["name"], it["category"], it["current_stock"],
                it["shelf_life_days"], it["average_daily_demand"], it.get("usable_shelf_life", "N/A"),
                it["recommended_reorder_qty"], it.get("shelf_life_note") or "Overstock relative to shelf life"
            ])
    else:
        filename = f"stocksense_report_{timestamp}.csv"
        writer.writerow(["Message"])
        writer.writerow(["Unknown report type"])

    return output.getvalue(), filename
