import json
import datetime
from typing import Dict, Any, List, Optional
from backend.database import get_db

def evaluate_and_generate_alerts(shop_id: int = 1) -> Dict[str, Any]:
    """
    Evaluates all rule-based alert conditions across inventory, forecasts, and orders.
    Deduplicates active open alerts and auto-resolves cleared conditions.
    """
    from backend.services.reorder_service import generate_reorder_plan
    
    db = get_db()
    cursor = db.cursor()

    plan = generate_reorder_plan(shop_id=shop_id)
    items = plan["items"]

    created_count = 0
    resolved_count = 0

    # Fetch currently OPEN alerts for this shop
    cursor.execute("SELECT id, alert_type, product_id FROM alerts WHERE shop_id = ? AND status = 'OPEN'", (shop_id,))
    open_alerts = {(row["alert_type"], row["product_id"]): row["id"] for row in cursor.fetchall()}

    active_conditions = set()

    def _upsert_alert(alert_type, dedup_k, severity, pid, sku, title, message, explanation):
        cursor.execute("""
            INSERT INTO alerts (shop_id, type, alert_type, dedup_key, severity, product_id, sku, title, message, explanation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            ON CONFLICT(dedup_key) DO UPDATE SET
                status = 'OPEN',
                severity = excluded.severity,
                title = excluded.title,
                message = excluded.message,
                explanation = excluded.explanation,
                resolved_at = NULL
        """, (shop_id, alert_type, alert_type, dedup_k, severity, pid, sku, title, message, explanation))

    # Rule 1 & 2: Stockout Imminent & Reorder Point Reached
    for it in items:
        pid = it["product_id"]
        sku = it["sku"]
        pname = it["name"]
        cur_stock = it["current_stock"]
        days_left = it["days_until_stockout"]
        lead_time = it["lead_time_days"]
        rop = it["reorder_point"]

        # Critical or High Stockout Imminent
        if it["priority"] == "CRITICAL":
            cond_key = ("STOCKOUT_IMMINENT", pid)
            active_conditions.add(cond_key)
            if cond_key not in open_alerts:
                dedup_k = f"shop_{shop_id}_STOCKOUT_IMMINENT_{pid}"
                _upsert_alert(
                    'STOCKOUT_IMMINENT', dedup_k, 'CRITICAL', pid, sku,
                    f"Critical Stockout Imminent: {sku}",
                    f"{pname} has only {cur_stock} units left (~{days_left}d demand), which is less than the {lead_time}d supplier lead time.",
                    it["recommendation_reason"]
                )
                created_count += 1
        elif it["priority"] == "HIGH":
            cond_key = ("STOCKOUT_IMMINENT", pid)
            active_conditions.add(cond_key)
            if cond_key not in open_alerts:
                dedup_k = f"shop_{shop_id}_STOCKOUT_IMMINENT_{pid}"
                _upsert_alert(
                    'STOCKOUT_IMMINENT', dedup_k, 'HIGH', pid, sku,
                    f"Safety Buffer Breached: {sku}",
                    f"{pname} inventory is breaching safety buffer thresholds with ~{days_left}d of supply remaining.",
                    it["recommendation_reason"]
                )
                created_count += 1

        # Reorder Point
        if cur_stock <= rop and it["recommended_reorder_qty"] > 0:
            cond_key = ("REORDER_POINT", pid)
            active_conditions.add(cond_key)
            if cond_key not in open_alerts:
                dedup_k = f"shop_{shop_id}_REORDER_POINT_{pid}"
                _upsert_alert(
                    'REORDER_POINT', dedup_k, 'MEDIUM', pid, sku,
                    f"Reorder Point Crossed: {sku}",
                    f"Stock level ({cur_stock} units) has dropped below Reorder Point of {rop} units.",
                    f"Order recommended: {it['recommended_reorder_qty']} units (Cost: ${it['purchase_cost']:,.2f})."
                )
                created_count += 1

        # Perishable Expiry Risk / Shelf Life Conflict
        if it["is_perishable"]:
            if it.get("shelf_life_capped"):
                cond_key = ("EXPIRY_RISK", pid)
                active_conditions.add(cond_key)
                if cond_key not in open_alerts:
                    dedup_k = f"shop_{shop_id}_EXPIRY_RISK_{pid}"
                    _upsert_alert(
                        'EXPIRY_RISK', dedup_k, 'HIGH', pid, sku,
                        f"Perishable Spoilage Cap Applied: {sku}",
                        f"Recommended order for {pname} was restricted by usable shelf-life limit.",
                        it.get("shelf_life_note") or "Capped to prevent overstock expiration."
                    )
                    created_count += 1

                    try:
                        from backend.services.notification_rules import evaluate_expiry_risk
                        from backend.workers.notification_worker import enqueue_notification
                        notif_spec = evaluate_expiry_risk(
                            product_name=pname,
                            sku=sku,
                            days_to_expiry=it.get("shelf_life_days") or 3,
                            product_id=pid
                        )
                        if notif_spec:
                            enqueue_notification(
                                rule=notif_spec["rule"],
                                title=notif_spec["title"],
                                message=notif_spec["message"],
                                priority=notif_spec["priority"],
                                tags=notif_spec["tags"],
                                event_ref=f"expiry_{pid}",
                                dedup_key=notif_spec["dedup_key"],
                                owner_id=1
                            )
                    except Exception:
                        pass

            if lead_time >= (it.get("shelf_life_days") or 999):
                cond_key = ("SHELF_LIFE_CONFLICT", pid)
                active_conditions.add(cond_key)
                if cond_key not in open_alerts:
                    dedup_k = f"shop_{shop_id}_SHELF_LIFE_CONFLICT_{pid}"
                    _upsert_alert(
                        'SHELF_LIFE_CONFLICT', dedup_k, 'CRITICAL', pid, sku,
                        f"Supplier Incompatible with Shelf Life: {sku}",
                        f"Supplier delivery time ({lead_time}d) meets or exceeds product shelf life ({it.get('shelf_life_days')}d).",
                        "Fresh delivery cannot be guaranteed. Switch to a faster regional supplier."
                    )
                    created_count += 1

        # Overstock detection (> 3x Target Stock)
        if it["target_stock"] > 0 and cur_stock > (it["target_stock"] * 3):
            cond_key = ("OVERSTOCK", pid)
            active_conditions.add(cond_key)
            if cond_key not in open_alerts:
                dedup_k = f"shop_{shop_id}_OVERSTOCK_{pid}"
                _upsert_alert(
                    'OVERSTOCK', dedup_k, 'MEDIUM', pid, sku,
                    f"Excess Capital Tied Up (Overstock): {sku}",
                    f"{pname} has {cur_stock} units on hand vs. target stock of {it['target_stock']}.",
                    "Working capital is locked. Avoid reordering until stock normalizes."
                )
                created_count += 1

    # Auto-resolve alerts that are no longer true!
    for (alert_type, pid), alert_id in open_alerts.items():
        if (alert_type, pid) not in active_conditions:
            # Condition has resolved!
            cursor.execute("""
                UPDATE alerts SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (alert_id,))
            resolved_count += 1

    db.commit()
    return {
        "status": "success",
        "new_alerts_created": created_count,
        "alerts_auto_resolved": resolved_count,
        "message": f"Alert rules evaluated: {created_count} new alerts created, {resolved_count} resolved automatically."
    }

def list_alerts(shop_id: int = 1, status: Optional[str] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM alerts WHERE shop_id = ?"
    params = [shop_id]

    if status and status != "all":
        query += " AND status = ?"
        params.append(status.upper())
    if severity and severity != "all":
        query += " AND severity = ?"
        params.append(severity.upper())

    query += " ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, created_at DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

def update_alert_status(alert_id: int, new_status: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    norm = new_status.upper()
    if norm not in ("OPEN", "ACKNOWLEDGED", "RESOLVED"):
        raise ValueError("Status must be OPEN, ACKNOWLEDGED, or RESOLVED")

    resolved_time = datetime.datetime.now().isoformat() if norm == "RESOLVED" else None
    cursor.execute("""
        UPDATE alerts SET status = ?, resolved_at = ? WHERE id = ?
    """, (norm, resolved_time, alert_id))
    db.commit()

    cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
