import math
from typing import Dict, Any, List, Optional
from backend.database import get_db
from backend.services.forecasting_service import forecast_demand
from backend.services.priority_service import evaluate_priority
from backend.services.order_service import get_incoming_units_by_sku

def calculate_product_reorder(
    product_dict: Dict[str, Any],
    window_days: int = 30,
    coverage_days: int = 14,
    forecast_method: str = "moving_average",
    shelf_life_buffer_days: int = 2,
    incoming_units_map: Optional[Dict[str, int]] = None,
    shop_id: int = 1
) -> Dict[str, Any]:
    """
    Computes replenishment plan enforcing supplier MOQ, pack rounding, incoming PO inventory positions,
    and a hard perishable shelf-life cap.
    """
    product_id = product_dict["id"]
    sku = product_dict["sku"].upper()
    name = product_dict["name"]
    category = product_dict["category"]
    current_stock = product_dict["current_stock"]
    unit_cost = product_dict["unit_cost"]
    selling_price = product_dict["selling_price"]
    lead_time_days = product_dict["lead_time_days"] or 7
    is_perishable = bool(product_dict["is_perishable"])
    shelf_life_days = product_dict.get("shelf_life_days")
    min_order_qty = max(1, product_dict.get("min_order_qty") or 1)
    pack_size = max(1, product_dict.get("pack_size") or 1)
    safety_buffer_days = max(1, product_dict.get("safety_buffer_days") or 3)

    # 1. Incoming Purchase Orders in transit
    incoming_units = 0
    if incoming_units_map and sku in incoming_units_map:
        incoming_units = incoming_units_map[sku]

    # Inventory Position = Current Stock + Incoming POs in transit
    inventory_position = current_stock + incoming_units

    # 2. Demand Forecast
    fc = forecast_demand(product_id, horizon_days=coverage_days, window_days=window_days, method=forecast_method, shop_id=shop_id)
    add = fc["average_daily_demand"]

    # 3. Replenishment Baseline Formulas
    lead_time_demand = round(add * lead_time_days, 2)
    safety_stock = round(add * safety_buffer_days, 2)
    reorder_point = round(lead_time_demand + safety_stock, 2)
    target_stock = round(add * (lead_time_days + coverage_days) + safety_stock, 2)

    # 4. Base Reorder Deficit
    raw_deficit = target_stock - inventory_position
    base_qty = max(0.0, raw_deficit)

    # 5. Pack-Size Rounding & Supplier MOQ on Base Quantity
    uncapped_order_qty = 0
    pack_rounding_applied = False
    moq_applied = False

    if base_qty > 0:
        units = math.ceil(base_qty)
        if pack_size > 1:
            packs = math.ceil(units / pack_size)
            if packs * pack_size > units:
                pack_rounding_applied = True
            units = packs * pack_size

        if units < min_order_qty:
            moq_applied = True
            units = min_order_qty

        uncapped_order_qty = units

    # 6. Hard Shelf-Life Cap (Section 9)
    shelf_life_cap: Optional[int] = None
    usable_selling_window: Optional[int] = None
    shelf_life_capped = False
    shelf_life_note: Optional[str] = None
    shelf_life_incompatible = False

    final_reorder_qty = uncapped_order_qty

    if is_perishable and shelf_life_days and shelf_life_days > 0:
        # Usable Selling Window = Shelf Life - Lead Time - Safety Buffer
        usable_selling_window = max(0, shelf_life_days - lead_time_days - shelf_life_buffer_days)
        
        if lead_time_days >= shelf_life_days or usable_selling_window <= 0:
            shelf_life_incompatible = True
            shelf_life_cap = 0
            final_reorder_qty = 0
            shelf_life_note = f"Lead time ({lead_time_days}d) >= Shelf life ({shelf_life_days}d). Delivery cannot guarantee freshness before expiry. Order blocked."
        else:
            # Maximum sellable units before expiration minus existing on-hand stock
            max_sellable = add * usable_selling_window
            shelf_life_cap = max(0, math.floor(max_sellable - current_stock))

            if uncapped_order_qty > shelf_life_cap:
                shelf_life_capped = True
                # Round down to pack size when capping
                capped_units = shelf_life_cap
                if pack_size > 1:
                    capped_units = (shelf_life_cap // pack_size) * pack_size

                if capped_units < min_order_qty and shelf_life_cap < min_order_qty:
                    final_reorder_qty = 0
                    shelf_life_note = f"Shelf-life cap ({shelf_life_cap} units) is below supplier MOQ ({min_order_qty} units). Cannot order without high spoilage risk."
                else:
                    final_reorder_qty = max(0, capped_units)
                    shelf_life_note = f"Order strictly capped from {uncapped_order_qty} to {final_reorder_qty} units based on {usable_selling_window}d usable selling window."

    purchase_cost = round(final_reorder_qty * unit_cost, 2)
    potential_revenue = round(final_reorder_qty * selling_price, 2)

    # 7. Priority Evaluation
    priority_info = evaluate_priority(
        current_stock=current_stock,
        avg_daily_demand=add,
        lead_time_days=lead_time_days,
        safety_buffer_days=safety_buffer_days,
        reorder_point=reorder_point,
        is_perishable=is_perishable,
        shelf_life_days=shelf_life_days
    )

    reasons = []
    if incoming_units > 0:
        reasons.append(f"{incoming_units} units already in transit on purchase orders.")

    if final_reorder_qty > 0:
        reasons.append(priority_info["primary_reason"])
        if pack_rounding_applied and not shelf_life_capped:
            reasons.append(f"Rounded up to full pack size ({pack_size} pk).")
        if moq_applied and not shelf_life_capped:
            reasons.append(f"Adjusted to meet supplier MOQ ({min_order_qty} units).")
        if shelf_life_capped and shelf_life_note:
            reasons.append(shelf_life_note)
    else:
        if shelf_life_incompatible:
            reasons.append(shelf_life_note)
        elif priority_info["expiry_risk"]:
            reasons.append(priority_info["primary_reason"])
        else:
            reasons.append(f"Inventory position ({inventory_position} units) covers Reorder Point ({reorder_point}). No order needed.")

    primary_reason = " | ".join(reasons)

    return {
        "product_id": product_id,
        "sku": sku,
        "name": name,
        "category": category,
        "current_stock": current_stock,
        "incoming_units": incoming_units,
        "inventory_position": inventory_position,
        "unit_cost": unit_cost,
        "selling_price": selling_price,
        "supplier_name": product_dict.get("supplier_name") or "Prime Wholesale Distributor",
        "lead_time_days": lead_time_days,
        "is_perishable": is_perishable,
        "shelf_life_days": shelf_life_days,
        "min_order_qty": min_order_qty,
        "pack_size": pack_size,
        "safety_buffer_days": safety_buffer_days,

        # Metrics
        "average_daily_demand": add,
        "lead_time_demand": lead_time_demand,
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "target_stock": target_stock,
        "base_quantity": round(base_qty, 1),
        "uncapped_order_qty": uncapped_order_qty,

        # Shelf Life & Hard Cap
        "usable_selling_window": usable_selling_window,
        "shelf_life_cap": shelf_life_cap,
        "shelf_life_capped": shelf_life_capped,
        "shelf_life_note": shelf_life_note,
        "shelf_life_incompatible": shelf_life_incompatible,

        # Constraints
        "pack_rounding_applied": pack_rounding_applied,
        "moq_applied": moq_applied,

        # Final Recommendation
        "recommended_reorder_qty": final_reorder_qty,
        "purchase_cost": purchase_cost,
        "potential_revenue": potential_revenue,

        # Priority & Explanations
        "priority": priority_info["priority"],
        "priority_score": priority_info["priority_score"],
        "days_until_stockout": priority_info["days_until_stockout"],
        "expiry_risk": priority_info["expiry_risk"],
        "signals": priority_info["signals"],
        "recommendation_reason": primary_reason,
        "all_reasons": reasons,

        "calculation_trace": {
            "formula_rop": f"LTD ({lead_time_demand}) + SS ({safety_stock}) = {reorder_point}",
            "formula_target": f"ADD ({add}) * ({lead_time_days} + {coverage_days}) + SS ({safety_stock}) = {target_stock}",
            "formula_inventory_position": f"Stock ({current_stock}) + Incoming ({incoming_units}) = {inventory_position}",
            "formula_base_qty": f"max(0, Target ({target_stock}) - Position ({inventory_position})) = {round(base_qty, 1)}",
            "coverage_days": coverage_days,
            "window_days": window_days
        }
    }

def generate_reorder_plan(
    category: Optional[str] = None,
    priority_filter: Optional[str] = None,
    search: Optional[str] = None,
    budget_limit: Optional[float] = None,
    shop_id: int = 1
) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}

    historical_window = int(settings.get("historical_window_days", 30))
    coverage_days = int(settings.get("coverage_days", 14))
    forecast_method = settings.get("forecast_method", "moving_average")
    shelf_life_buffer = int(settings.get("shelf_life_buffer_days", 2))
    default_budget = float(settings.get("budget", 0.0))
    active_budget = budget_limit if budget_limit is not None else (default_budget if default_budget > 0 else None)

    # Get incoming purchase orders
    incoming_map = get_incoming_units_by_sku(shop_id=shop_id)

    cursor.execute("""
        SELECT p.*, s.name as supplier_name, s.lead_time as supplier_lead_time
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.shop_id = ? AND p.is_active = 1
    """, (shop_id,))
    products = [dict(row) for row in cursor.fetchall()]

    reorder_items = []
    for p in products:
        item = calculate_product_reorder(
            p,
            window_days=historical_window,
            coverage_days=coverage_days,
            forecast_method=forecast_method,
            shelf_life_buffer_days=shelf_life_buffer,
            incoming_units_map=incoming_map,
            shop_id=shop_id
        )
        reorder_items.append(item)

    # Deterministic Sort: By priority_score DESC, days_until_stockout ASC, name ASC
    reorder_items.sort(key=lambda x: (-x["priority_score"], x["days_until_stockout"], x["name"]))

    # Budget Allocation Constraint
    budget_applied = False
    allocated_cost = 0.0
    if active_budget and active_budget > 0:
        budget_applied = True
        current_spent = 0.0
        for item in reorder_items:
            if item["recommended_reorder_qty"] > 0:
                cost = item["purchase_cost"]
                if current_spent + cost <= active_budget:
                    current_spent += cost
                else:
                    affordable_qty = max(0, int((active_budget - current_spent) // item["unit_cost"]))
                    if affordable_qty < item["recommended_reorder_qty"]:
                        item["budget_capped"] = True
                        item["original_qty"] = item["recommended_reorder_qty"]
                        item["recommended_reorder_qty"] = affordable_qty
                        item["purchase_cost"] = round(affordable_qty * item["unit_cost"], 2)
                        current_spent += item["purchase_cost"]
                        item["recommendation_reason"] += f" | Capped to {affordable_qty} to fit budget limit of ${active_budget:,.2f}."
        allocated_cost = current_spent

    total_products = len(reorder_items)
    products_requiring_reorder = sum(1 for x in reorder_items if x["recommended_reorder_qty"] > 0)
    critical_stockouts = sum(1 for x in reorder_items if x["priority"] == "CRITICAL")
    high_urgency = sum(1 for x in reorder_items if x["priority"] == "HIGH")
    medium_urgency = sum(1 for x in reorder_items if x["priority"] == "MEDIUM")
    healthy_count = sum(1 for x in reorder_items if x["priority"] == "HEALTHY")
    expiry_risk_count = sum(1 for x in reorder_items if x["expiry_risk"])
    capped_by_shelf_life_count = sum(1 for x in reorder_items if x.get("shelf_life_capped") or x.get("shelf_life_incompatible"))
    total_reorder_value = round(sum(x["purchase_cost"] for x in reorder_items), 2)
    total_reorder_units = sum(x["recommended_reorder_qty"] for x in reorder_items)

    filtered_items = reorder_items
    if category and category != "all":
        filtered_items = [x for x in filtered_items if x["category"] == category]
    if priority_filter and priority_filter != "all":
        filtered_items = [x for x in filtered_items if x["priority"] == priority_filter]
    if search:
        s_term = search.strip().lower()
        filtered_items = [
            x for x in filtered_items
            if s_term in x["name"].lower() or s_term in x["sku"].lower() or s_term in x["category"].lower()
        ]

    return {
        "summary": {
            "total_products": total_products,
            "products_requiring_reorder": products_requiring_reorder,
            "critical_stockouts": critical_stockouts,
            "high_urgency": high_urgency,
            "medium_urgency": medium_urgency,
            "healthy_count": healthy_count,
            "expiry_risk_count": expiry_risk_count,
            "capped_by_shelf_life_count": capped_by_shelf_life_count,
            "total_reorder_value": total_reorder_value,
            "total_reorder_units": total_reorder_units,
            "budget_limit": active_budget,
            "budget_applied": budget_applied,
            "allocated_cost": allocated_cost if budget_applied else total_reorder_value
        },
        "settings": {
            "historical_window_days": historical_window,
            "coverage_days": coverage_days,
            "forecast_method": forecast_method,
            "shelf_life_buffer_days": shelf_life_buffer
        },
        "items": filtered_items
    }
