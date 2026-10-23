"""
StockSense AI - End-to-End Comprehensive Verification Script
Executes all 4 actor lifecycles (Retailer, Wholesaler, Dealer, Admin)
Verifies:
- Live barcode/QR scan
- Cart & Payment settlement with HMAC webhook
- Inventory movement audit logging (Rule 5)
- Location stock & box scan reconciliation
- Push notification dispatch
- Past records & data import
- 4-role RBAC enforcement
- Financial precision in integer paise (Rule 4)
"""

import sys
import os
import json
import hmac
import hashlib
import datetime

# Ensure project root in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app import create_app
from backend.database import get_db, init_db
from backend.services.auth_service import switch_demo_role, verify_token
from backend.services.notifier import publish_notification
from backend.repositories.location_repository import LocationRepository
from backend.services.location_service import seed_demo_locations

def run_verification():
    app = create_app({"TESTING": True})
    results = []

    def record_step(step_num: int, phase: str, description: str, passed: bool, details: dict):
        results.append({
            "step": step_num,
            "phase": phase,
            "description": description,
            "status": "PASS" if passed else "FAIL",
            "details": details
        })
        status_sym = "[PASS]" if passed else "[FAIL]"
        print(f" {status_sym} Step {step_num:02d}: [{phase}] {description}")

    with app.test_client() as client:
        with app.app_context():
            init_db()
            seed_demo_locations()

            print("=" * 75)
            print("STOCKSENSE AI - END-TO-END VERIFICATION RUNNER")
            print(f"Timestamp: {datetime.datetime.now().isoformat()}")
            print("=" * 75)

            # ==============================================================
            # PHASE 1 & 6: RETAILER AUTHENTICATION & BARCODE SCAN
            # ==============================================================
            user_ret = switch_demo_role("retailer")
            ret_headers = {"X-User-Role": "retailer", "Authorization": f"Bearer {user_ret['token']}"}
            record_step(1, "Retailer", "Authenticate Retailer & Issue JWT/Token", user_ret["role"] == "retailer", {"email": user_ret["email"]})

            # Fetch initial stock for SKU-MLK-01
            db = get_db()
            c = db.cursor()
            c.execute("SELECT id, sku, name, current_stock, selling_price FROM products WHERE sku = 'SKU-MLK-01'")
            prod_row = dict(c.fetchone())
            initial_stock = prod_row["current_stock"]

            # Step 2: Barcode recognition
            res_rec = client.post("/api/scanner/recognize", json={"barcode": "8901262010053"}, headers=ret_headers)
            rec_data = res_rec.get_json()
            rec_ok = res_rec.status_code == 200 and rec_data.get("matched") and rec_data["product"]["sku"] == "SKU-MLK-01"
            record_step(2, "Retailer", "Scan Barcode 8901262010053 (Amul Taaza Milk)", rec_ok, {
                "matched_sku": rec_data.get("product", {}).get("sku"),
                "confidence": rec_data.get("confidence")
            })

            # ==============================================================
            # PAYMENT GENERATION & HMAC WEBHOOK SETTLEMENT (RULE 4 & 5)
            # ==============================================================
            # Step 3: Generate UPI Payment Request
            # Price is ₹54.00 = 5400 paise
            amount_inr = 54.00
            res_qr = client.post("/api/payment/generate-qr", json={"amount": amount_inr, "purpose": "pos_checkout"}, headers=ret_headers)
            qr_data = res_qr.get_json()
            qr_ok = res_qr.status_code == 200 and "upi_uri" in qr_data and qr_data.get("amount_paise") == 5400
            txn_ref = qr_data.get("transaction_ref")
            record_step(3, "Payments", "Generate Dynamic UPI QR & Integer Paise (INR 54.00 -> 5400 paise)", qr_ok, {
                "upi_uri": qr_data.get("upi_uri"),
                "amount_paise": qr_data.get("amount_paise"),
                "txn_ref": txn_ref
            })

            # Step 4: Payment Webhook with HMAC-SHA256
            import uuid
            dynamic_utr = f"UTR{uuid.uuid4().hex[:12].upper()}"
            webhook_secret = os.environ.get("PAYMENT_WEBHOOK_SECRET", "stocksense_whsec_demo_2026")
            webhook_payload = json.dumps({
                "transaction_ref": txn_ref,
                "amount": amount_inr,
                "utr_number": dynamic_utr,
                "cart_items": [{"product_id": prod_row["id"], "sku": prod_row["sku"], "quantity": 1}]
            }).encode("utf-8")

            sig = hmac.new(webhook_secret.encode("utf-8"), webhook_payload, hashlib.sha256).hexdigest()
            res_wh = client.post("/api/payment/webhook", data=webhook_payload, headers={
                "Content-Type": "application/json",
                "X-StockSense-Signature": sig
            })
            wh_data = res_wh.get_json() or {}
            wh_ok = res_wh.status_code == 200 and wh_data.get("status") == "SUCCESS" and wh_data.get("verified") is True
            record_step(4, "Payments", "Webhook Verification & Inventory Settlement via HMAC-SHA256", wh_ok, {
                "status": wh_data.get("status"),
                "verified": wh_data.get("verified"),
                "amount_settled": wh_data.get("amount_settled")
            })

            # Step 5: Verify Rule 5 (Inventory Movement row created)
            db.commit()
            c.execute("SELECT id, sku, current_stock FROM products WHERE sku = 'SKU-MLK-01'")
            updated_stock = c.fetchone()["current_stock"]
            c.execute("SELECT delta, balance_after, reason FROM inventory_movements WHERE product_id = ? ORDER BY id DESC LIMIT 1", (prod_row["id"],))
            mov_row = dict(c.fetchone())
            stock_decremented = updated_stock == (initial_stock - 1)
            mov_logged = mov_row["reason"] in ("SALE", "UPI_CHECKOUT_SETTLED") and mov_row["delta"] < 0
            record_step(5, "Inventory", "Rule 5 Audit: Stock decremented & inventory_movements row logged", stock_decremented and mov_logged, {
                "initial_stock": initial_stock,
                "new_stock": updated_stock,
                "movement": mov_row
            })

            # ==============================================================
            # PHASE 3: WAREHOUSE LOCATIONS & BOX SCAN RECONCILIATION
            # ==============================================================
            # Wholesaler receives crate at Location #3 (Box BX-01)
            user_wh = switch_demo_role("wholesaler")
            wh_headers = {"X-User-Role": "wholesaler", "Authorization": f"Bearer {user_wh['token']}"}

            # Set expected stock in BX-01 (Location 3) for SKU-MLK-01 to 24 units
            LocationRepository.set_location_stock(location_id=3, sku="SKU-MLK-01", expected_qty=24)

            # Perform Box Scan reconciliation with 20 items found (4 missing -> LOCATION_MISMATCH)
            res_box = client.post("/api/locations/3/box-scan", json={"scanned_counts": {"SKU-MLK-01": 20}}, headers=wh_headers)
            box_data = res_box.get_json()
            recon = box_data.get("reconciliation", {})
            mismatch_detected = recon.get("mismatch_count", 0) > 0 and len(recon.get("alerts_created", [])) > 0
            record_step(6, "Wholesale/Locations", "Box Scan Reconciliation: Detected count discrepancy & alert", mismatch_detected, {
                "expected": 24,
                "actual": 20,
                "mismatches": recon.get("mismatch_count"),
                "alerts": recon.get("alerts_created")
            })

            # ==============================================================
            # PHASE 5: PUSH NOTIFICATIONS
            # ==============================================================
            # Dispatch low stock alert
            notif_res = publish_notification(
                rule_type="LOW_STOCK",
                title="Low Stock Alert: Amul Milk",
                message=f"Stock of SKU-MLK-01 reached {updated_stock} units. Immediate reorder recommended.",
                tags=["warning", "package"],
                dedup_key=f"low_stock_mlk_{updated_stock}"
            )
            record_step(7, "Push Notifications", "ntfy.sh Multi-Channel Push Notification Dispatched", notif_res.get("status") in ("sent", "deduped"), {
                "rule_type": "LOW_STOCK",
                "dedup_key": notif_res.get("dedup_key"),
                "status": notif_res.get("status")
            })

            # ==============================================================
            # PHASE 4: DATA PIPELINE & RECORDS AUDIT
            # ==============================================================
            # Query past sales and movements history
            res_past_sales = client.get("/api/records/sales?group_by=day", headers=ret_headers)
            res_past_mov = client.get("/api/records/stock-movements", headers=ret_headers)
            records_ok = res_past_sales.status_code == 200 and res_past_mov.status_code == 200
            record_step(8, "Data Pipeline", "Query Past Sales & Inventory Movements Audit Trail", records_ok, {
                "daily_sales_records": len(res_past_sales.get_json().get("sales", [])),
                "movements_count": len(res_past_mov.get_json().get("movements", []))
            })

            # ==============================================================
            # PHASE 6: DEALER LIFECYCLE & 4-ROLE RBAC ISOLATION
            # ==============================================================
            user_dealer = switch_demo_role("dealer")
            dealer_headers = {"X-User-Role": "dealer", "Authorization": f"Bearer {user_dealer['token']}"}

            # Dealer dispatches & allocations
            res_dsp = client.get("/api/dealer/dispatches", headers=dealer_headers)
            res_tiers = client.get("/api/dealer/pricing-tiers", headers=dealer_headers)
            res_alloc = client.get("/api/dealer/allocations", headers=dealer_headers)
            dealer_ok = res_dsp.status_code == 200 and res_tiers.status_code == 200 and res_alloc.status_code == 200
            record_step(9, "Dealer", "Dealer Capabilities: Dispatches, Pricing Tiers & Regional Allocations", dealer_ok, {
                "dispatches": len(res_dsp.get_json().get("dispatches", [])),
                "pricing_tiers": len(res_tiers.get_json().get("tiers", [])),
                "allocations": len(res_alloc.get_json().get("allocations", []))
            })

            # Role Boundaries: Retailer blocked from Admin
            res_ret_admin = client.get("/api/admin/users", headers=ret_headers)
            # Wholesaler blocked from POS quick sale
            res_wh_pos = client.post("/api/scanner/quick-sale", json={"product_id": 1, "quantity": 1}, headers=wh_headers)
            # Dealer blocked from internal store locations
            res_dlr_loc = client.get("/api/locations", headers=dealer_headers)

            rbac_ok = (
                res_ret_admin.status_code == 403 and
                res_wh_pos.status_code == 403 and
                res_dlr_loc.status_code == 403
            )
            record_step(10, "RBAC Security", "Strict Role & Tenant Boundary Enforcement (403 on forbidden access)", rbac_ok, {
                "retailer_on_admin": res_ret_admin.status_code,
                "wholesaler_on_pos": res_wh_pos.status_code,
                "dealer_on_locations": res_dlr_loc.status_code
            })

            # ==============================================================
            # DASHBOARD TOTALS FOR ALL 4 ROLES
            # ==============================================================
            res_ret_dash = client.get("/api/dashboard", headers=ret_headers)
            res_wh_dash = client.get("/api/dashboard", headers=wh_headers)
            res_dlr_dash = client.get("/api/dashboard", headers=dealer_headers)
            res_adm_dash = client.get("/api/dashboard", headers={"X-User-Role": "admin"})

            dashboards_ok = (
                res_ret_dash.status_code == 200 and res_ret_dash.get_json()["role"] == "retailer" and
                res_wh_dash.status_code == 200 and res_wh_dash.get_json()["role"] == "wholesaler" and
                res_dlr_dash.status_code == 200 and res_dlr_dash.get_json()["role"] == "dealer" and
                res_adm_dash.status_code == 200 and res_adm_dash.get_json()["role"] == "admin"
            )
            record_step(11, "Dashboard", "Tailored Multi-Role Dashboards (Retailer, Wholesaler, Dealer, Admin)", dashboards_ok, {
                "retailer_summary_items": len(res_ret_dash.get_json().get("summary", {})),
                "wholesaler_catalog_items": res_wh_dash.get_json().get("summary", {}).get("catalog_items"),
                "dealer_territory": res_dlr_dash.get_json().get("dealer_territory"),
                "admin_active_users": res_adm_dash.get_json().get("summary", {}).get("active_users")
            })

            print("=" * 75)
            total_steps = len(results)
            passed_steps = sum(1 for r in results if r["status"] == "PASS")
            print(f"VERIFICATION SUMMARY: {passed_steps}/{total_steps} Passed ({(passed_steps/total_steps)*100:.1f}%)")
            print("=" * 75)

            return results

if __name__ == "__main__":
    res = run_verification()
    all_passed = all(r["status"] == "PASS" for r in res)
    sys.exit(0 if all_passed else 1)
