import math
from typing import Dict, Any, List, Tuple

def evaluate_priority(
    current_stock: int,
    avg_daily_demand: float,
    lead_time_days: int,
    safety_buffer_days: int,
    reorder_point: float,
    is_perishable: bool = False,
    shelf_life_days: int = None
) -> Dict[str, Any]:
    """
    Evaluates urgency and assigns an explainable priority level:
    CRITICAL, HIGH, MEDIUM, HEALTHY.
    Also flags EXPIRY_RISK for perishable items.
    """
    signals: List[Dict[str, str]] = []
    explanations: List[str] = []

    # 1. Days until stockout
    if avg_daily_demand > 0:
        days_until_stockout = round(current_stock / avg_daily_demand, 1)
    else:
        days_until_stockout = 999.0 if current_stock > 0 else 0.0

    # 2. Expiry & Spoilage signals
    expiry_risk = False
    shelf_life_warning = None
    if is_perishable and shelf_life_days and shelf_life_days > 0:
        max_sellable_before_spoil = avg_daily_demand * shelf_life_days
        if current_stock > max_sellable_before_spoil:
            expiry_risk = True
            excess_units = int(current_stock - max_sellable_before_spoil)
            signals.append({
                "type": "EXPIRY_RISK",
                "severity": "high",
                "message": f"Overstock Spoilage Risk: Current inventory exceeds {shelf_life_days}-day demand by ~{excess_units} units."
            })
            explanations.append(f"At risk of expiring before sale (~{excess_units} excess units based on {shelf_life_days}-day shelf life).")

        if lead_time_days >= shelf_life_days:
            shelf_life_warning = f"Supplier lead time ({lead_time_days} days) is >= shelf life ({shelf_life_days} days). Critical supplier delivery risk."
            signals.append({
                "type": "LEAD_TIME_EXPIRY_CONFLICT",
                "severity": "critical",
                "message": shelf_life_warning
            })
            explanations.append(shelf_life_warning)

    # 3. Stockout Urgency Classification
    priority = "HEALTHY"
    priority_score = 0  # Numeric score for deterministic sorting (100 = most critical)

    if current_stock <= 0 and avg_daily_demand > 0:
        priority = "CRITICAL"
        priority_score = 100
        signals.append({
            "type": "STOCKOUT",
            "severity": "critical",
            "message": "Completely out of stock with active customer demand."
        })
        explanations.append("Out of stock: immediate replenishment required to stop lost sales.")
    elif days_until_stockout <= lead_time_days and avg_daily_demand > 0:
        priority = "CRITICAL"
        # The fewer days left relative to lead time, the higher the score
        gap = max(0, lead_time_days - days_until_stockout)
        priority_score = 80 + min(19, int(gap * 2))
        signals.append({
            "type": "STOCKOUT_BEFORE_DELIVERY",
            "severity": "critical",
            "message": f"Stock will deplete in ~{days_until_stockout} days, before supplier delivery ({lead_time_days} days)."
        })
        explanations.append(f"Stock will run out in {days_until_stockout} days, which is less than the {lead_time_days}-day supplier lead time.")
    elif days_until_stockout <= (lead_time_days + safety_buffer_days) and avg_daily_demand > 0:
        priority = "HIGH"
        priority_score = 60 + min(19, int((lead_time_days + safety_buffer_days - days_until_stockout) * 2))
        signals.append({
            "type": "SAFETY_BUFFER_BREACHED",
            "severity": "high",
            "message": f"Stock depleting within safety buffer window ({days_until_stockout} days remaining vs {lead_time_days + safety_buffer_days} day target threshold)."
        })
        explanations.append(f"Inventory will breach the {safety_buffer_days}-day safety buffer before standard reorder arrival.")
    elif current_stock <= reorder_point and avg_daily_demand > 0:
        priority = "MEDIUM"
        priority_score = 40 + min(19, int((reorder_point - current_stock) / max(1, reorder_point) * 19))
        signals.append({
            "type": "REORDER_POINT_REACHED",
            "severity": "medium",
            "message": f"Inventory ({current_stock} units) has crossed the Reorder Point ({round(reorder_point, 1)} units)."
        })
        explanations.append(f"Stock ({current_stock}) has dropped below Reorder Point ({round(reorder_point, 1)}). Replenish to maintain smooth coverage.")
    else:
        priority = "HEALTHY"
        priority_score = max(0, 20 - int(days_until_stockout / 10))
        signals.append({
            "type": "STOCK_HEALTHY",
            "severity": "low",
            "message": f"Stock level is sufficient for ~{days_until_stockout if days_until_stockout < 999 else '90+'} days."
        })
        explanations.append(f"Stock is healthy with sufficient buffer coverage.")

    primary_reason = explanations[0] if explanations else "Inventory level matches target coverage."

    return {
        "priority": priority,
        "priority_score": priority_score,
        "days_until_stockout": days_until_stockout,
        "expiry_risk": expiry_risk,
        "shelf_life_warning": shelf_life_warning,
        "signals": signals,
        "primary_reason": primary_reason,
        "all_reasons": explanations
    }
