import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models.orm_models import Location, LocationStock, Product, Alert
from backend.database import get_db_session

class LocationRepository:
    """Repository for physical storage hierarchy (shelves, bins, boxes) and location stock."""

    @staticmethod
    def create_location(
        name: str,
        location_type: str = "shelf",
        barcode: Optional[str] = None,
        parent_id: Optional[int] = None,
        description: Optional[str] = None,
        shop_id: int = 1
    ) -> Dict[str, Any]:
        with get_db_session() as session:
            if barcode:
                existing = session.query(Location).filter(Location.barcode == barcode).first()
                if existing:
                    existing.name = name
                    existing.location_type = location_type
                    existing.parent_id = parent_id
                    existing.description = description
                    session.flush()
                    return {
                        "id": existing.id,
                        "name": existing.name,
                        "location_type": existing.location_type,
                        "barcode": existing.barcode,
                        "parent_id": existing.parent_id,
                        "description": existing.description,
                        "shop_id": existing.shop_id
                    }

            loc = Location(
                name=name,
                location_type=location_type,
                barcode=barcode,
                parent_id=parent_id,
                description=description,
                shop_id=shop_id
            )
            session.add(loc)
            session.flush()
            return {
                "id": loc.id,
                "name": loc.name,
                "location_type": loc.location_type,
                "barcode": loc.barcode,
                "parent_id": loc.parent_id,
                "description": loc.description,
                "shop_id": loc.shop_id
            }

    @staticmethod
    def list_locations(shop_id: int = 1) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            locations = session.query(Location).filter(Location.shop_id == shop_id).all()
            result = []
            for loc in locations:
                parent_name = loc.parent.name if loc.parent else None
                stock_summary = [
                    {
                        "id": s.id,
                        "sku": s.sku,
                        "product_name": s.product.name if s.product else s.sku,
                        "expected_quantity": s.expected_quantity,
                        "actual_quantity": s.actual_quantity,
                        "status": s.status,
                        "last_counted_at": s.last_counted_at.isoformat() if s.last_counted_at else None
                    }
                    for s in loc.stock_items
                ]
                result.append({
                    "id": loc.id,
                    "name": loc.name,
                    "location_type": loc.location_type,
                    "barcode": loc.barcode,
                    "parent_id": loc.parent_id,
                    "parent_name": parent_name,
                    "description": loc.description,
                    "stock_items": stock_summary,
                    "created_at": loc.created_at.isoformat() if loc.created_at else None
                })
            return result

    @staticmethod
    def get_location(location_id: int) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            loc = session.query(Location).filter(Location.id == location_id).first()
            if not loc:
                return None
            return {
                "id": loc.id,
                "name": loc.name,
                "location_type": loc.location_type,
                "barcode": loc.barcode,
                "parent_id": loc.parent_id,
                "parent_name": loc.parent.name if loc.parent else None,
                "description": loc.description,
                "stock_items": [
                    {
                        "id": s.id,
                        "sku": s.sku,
                        "product_name": s.product.name if s.product else s.sku,
                        "expected_quantity": s.expected_quantity,
                        "actual_quantity": s.actual_quantity,
                        "status": s.status,
                        "last_counted_at": s.last_counted_at.isoformat() if s.last_counted_at else None
                    }
                    for s in loc.stock_items
                ]
            }

    @staticmethod
    def set_location_stock(location_id: int, sku: str, expected_qty: int) -> Dict[str, Any]:
        with get_db_session() as session:
            prod = session.query(Product).filter(Product.sku == sku).first()
            if not prod:
                raise ValueError(f"Product with SKU '{sku}' not found")

            stock = session.query(LocationStock).filter(
                LocationStock.location_id == location_id,
                LocationStock.sku == sku
            ).first()

            if stock:
                stock.expected_quantity = expected_qty
            else:
                stock = LocationStock(
                    location_id=location_id,
                    product_id=prod.id,
                    sku=sku,
                    expected_quantity=expected_qty,
                    actual_quantity=0,
                    status="MATCH" if expected_qty == 0 else "MISMATCH_SHORTAGE"
                )
                session.add(stock)

            session.flush()
            return {
                "id": stock.id,
                "location_id": stock.location_id,
                "sku": stock.sku,
                "expected_quantity": stock.expected_quantity,
                "actual_quantity": stock.actual_quantity,
                "status": stock.status
            }

    @staticmethod
    def reconcile_box_counts(location_id: int, scanned_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Compares scanned counts against expected counts for a location.
        Generates discrepancy alerts on mismatches.
        """
        now = datetime.datetime.utcnow()
        with get_db_session() as session:
            loc = session.query(Location).filter(Location.id == location_id).first()
            if not loc:
                raise ValueError(f"Location ID {location_id} not found")

            existing_stock = {s.sku: s for s in loc.stock_items}
            reconciled = []
            mismatches = []

            # Process all expected SKUs
            all_skus = set(existing_stock.keys()) | set(scanned_counts.keys())
            for sku in all_skus:
                actual = scanned_counts.get(sku, 0)
                item = existing_stock.get(sku)

                if item:
                    item.actual_quantity = actual
                    item.last_counted_at = now
                    expected = item.expected_quantity
                else:
                    # New unexpected item found in box
                    prod = session.query(Product).filter(Product.sku == sku).first()
                    prod_id = prod.id if prod else 1
                    item = LocationStock(
                        location_id=location_id,
                        product_id=prod_id,
                        sku=sku,
                        expected_quantity=0,
                        actual_quantity=actual,
                        last_counted_at=now
                    )
                    session.add(item)
                    expected = 0

                if actual == expected:
                    item.status = "MATCH"
                elif actual < expected:
                    item.status = "MISMATCH_SHORTAGE"
                    diff = actual - expected
                    mismatches.append({"sku": sku, "expected": expected, "actual": actual, "diff": diff})
                else:
                    item.status = "MISMATCH_SURPLUS"
                    diff = actual - expected
                    mismatches.append({"sku": sku, "expected": expected, "actual": actual, "diff": diff})

                reconciled.append({
                    "sku": sku,
                    "expected_quantity": expected,
                    "actual_quantity": actual,
                    "difference": actual - expected,
                    "status": item.status
                })

            # Create Alert on mismatch
            created_alerts = []
            if mismatches:
                summary_lines = [f"{m['sku']}: Expected {m['expected']}, Scanned {m['actual']} ({m['diff']:+d})" for m in mismatches]
                alert_title = f"Location Count Mismatch in '{loc.name}'"
                alert_msg = f"Audited {len(mismatches)} discrepancies during Box Scan: {'; '.join(summary_lines)}"
                dedup_key = f"mismatch_{loc.id}_{now.strftime('%Y%m%d%H%M%S%f')}"

                alert = Alert(
                    shop_id=loc.shop_id,
                    type="LOCATION_MISMATCH",
                    alert_type="LOCATION_MISMATCH",
                    severity="HIGH",
                    title=alert_title,
                    message=alert_msg,
                    explanation=f"Physical inventory count did not match expected database position in {loc.name} ({loc.location_type}).",
                    dedup_key=dedup_key,
                    status="OPEN"
                )
                session.add(alert)
                created_alerts.append(alert_title)

                try:
                    from backend.services.notification_rules import evaluate_count_mismatch
                    from backend.workers.notification_worker import enqueue_notification
                    first_m = mismatches[0]
                    notif_spec = evaluate_count_mismatch(
                        location_name=loc.name,
                        sku=first_m["sku"],
                        product_name=first_m["sku"],
                        difference=first_m["diff"],
                        expected_qty=first_m["expected"],
                        actual_qty=first_m["actual"],
                        location_id=loc.id
                    )
                    if notif_spec:
                        enqueue_notification(
                            rule=notif_spec["rule"],
                            title=notif_spec["title"],
                            message=notif_spec["message"],
                            priority=notif_spec["priority"],
                            tags=notif_spec["tags"],
                            event_ref=f"box_mismatch_{loc.id}_{now.strftime('%Y%m%d%H%M%S')}",
                            dedup_key=notif_spec["dedup_key"],
                            owner_id=1,
                            db_session=session
                        )
                except Exception:
                    pass

            session.flush()

            return {
                "location_id": loc.id,
                "location_name": loc.name,
                "location_type": loc.location_type,
                "total_skus_checked": len(reconciled),
                "mismatch_count": len(mismatches),
                "reconciled_items": reconciled,
                "alerts_created": created_alerts
            }
