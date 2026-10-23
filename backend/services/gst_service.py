import csv
import io
import uuid
import datetime
import re
from typing import Dict, Any, List, Optional
from backend.database import get_db

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

def validate_and_preview_gst_csv(file_content: str, filename: str, shop_id: int = 1) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    # Load active SKUs
    cursor.execute("SELECT sku, id, name FROM products WHERE shop_id = ? AND (is_active = 1 OR is_active IS NULL)", (shop_id,))
    product_map = {row["sku"].upper(): row for row in cursor.fetchall()}

    # Load HSN mappings
    cursor.execute("SELECT hsn_code, item_description, mapped_sku FROM gst_mappings WHERE shop_id = ?", (shop_id,))
    hsn_map = {row["hsn_code"].strip(): row["mapped_sku"].upper() for row in cursor.fetchall() if row["hsn_code"]}
    desc_map = {row["item_description"].strip().lower(): row["mapped_sku"].upper() for row in cursor.fetchall() if row["item_description"]}

    if not file_content or not file_content.strip():
        return {
            "batch_id": None, "filename": filename, "total_rows": 0, "valid_count": 0,
            "invalid_count": 0, "is_valid": False, "error": "GST CSV file is empty.",
            "valid_rows": [], "invalid_rows": [], "unmapped_rows": []
        }

    reader = csv.reader(io.StringIO(file_content.strip()))
    try:
        headers = [h.strip().lower() for h in next(reader, [])]
    except Exception as e:
        return {"error": f"Failed to parse CSV header: {str(e)}", "is_valid": False}

    required_cols = {"invoice_no", "invoice_date", "supply_type", "quantity"}
    missing = required_cols - set(headers)
    if missing:
        return {
            "error": f"Missing required GST columns: {', '.join(sorted(missing))}. Expected headers include: invoice_no, invoice_date, supply_type, quantity, hsn_code, item_description, sku",
            "is_valid": False, "total_rows": 0, "valid_count": 0, "invalid_count": 0
        }

    inv_idx = headers.index("invoice_no")
    date_idx = headers.index("invoice_date")
    type_idx = headers.index("supply_type")
    qty_idx = headers.index("quantity")
    gstin_idx = headers.index("gstin_counterparty") if "gstin_counterparty" in headers else None
    hsn_idx = headers.index("hsn_code") if "hsn_code" in headers else None
    desc_idx = headers.index("item_description") if "item_description" in headers else None
    sku_idx = headers.index("sku") if "sku" in headers else None
    val_idx = headers.index("total_value") if "total_value" in headers else None
    tax_idx = headers.index("taxable_value") if "taxable_value" in headers else None
    rate_idx = headers.index("gst_rate") if "gst_rate" in headers else None

    valid_rows = []
    invalid_rows = []
    unmapped_rows = []
    batch_id = str(uuid.uuid4())

    row_num = 1
    for row in reader:
        row_num += 1
        if not row or not any(field.strip() for field in row):
            continue

        raw_inv = row[inv_idx].strip() if len(row) > inv_idx else ""
        raw_date = row[date_idx].strip() if len(row) > date_idx else ""
        raw_type = row[type_idx].strip().lower() if len(row) > type_idx else ""
        raw_qty = row[qty_idx].strip() if len(row) > qty_idx else ""
        raw_gstin = row[gstin_idx].strip().upper() if gstin_idx is not None and len(row) > gstin_idx else ""
        raw_hsn = row[hsn_idx].strip() if hsn_idx is not None and len(row) > hsn_idx else ""
        raw_desc = row[desc_idx].strip() if desc_idx is not None and len(row) > desc_idx else ""
        raw_sku = row[sku_idx].strip().upper() if sku_idx is not None and len(row) > sku_idx else ""
        raw_val = float(row[val_idx].strip()) if val_idx is not None and len(row) > val_idx and row[val_idx].strip() else 0.0
        raw_tax = float(row[tax_idx].strip()) if tax_idx is not None and len(row) > tax_idx and row[tax_idx].strip() else 0.0
        raw_rate = float(row[rate_idx].strip()) if rate_idx is not None and len(row) > rate_idx and row[rate_idx].strip() else 0.0

        if not raw_inv:
            invalid_rows.append({"row_number": row_num, "reason": "Missing invoice number", "raw_data": ",".join(row)})
            continue

        # Validate date
        try:
            parsed_date = datetime.date.fromisoformat(raw_date)
            date_clean = parsed_date.isoformat()
        except Exception:
            invalid_rows.append({"row_number": row_num, "reason": f"Invalid date '{raw_date}'. Must be YYYY-MM-DD", "raw_data": ",".join(row)})
            continue

        # Validate supply type
        if raw_type not in ("outward", "inward", "sales", "purchase"):
            invalid_rows.append({"row_number": row_num, "reason": f"Invalid supply type '{raw_type}'. Expected 'outward' (sales) or 'inward' (purchase).", "raw_data": ",".join(row)})
            continue
        norm_type = "outward" if raw_type in ("outward", "sales") else "inward"

        # Validate quantity
        try:
            qty_val = float(raw_qty)
            if qty_val <= 0:
                invalid_rows.append({"row_number": row_num, "reason": "Quantity must be > 0", "raw_data": ",".join(row)})
                continue
        except ValueError:
            invalid_rows.append({"row_number": row_num, "reason": f"Quantity '{raw_qty}' is non-numeric", "raw_data": ",".join(row)})
            continue

        # Validate GSTIN if present
        if raw_gstin and not GSTIN_REGEX.match(raw_gstin):
            invalid_rows.append({"row_number": row_num, "reason": f"Invalid GSTIN format '{raw_gstin}' (Expected 15-character Indian GSTIN)", "raw_data": ",".join(row)})
            continue

        # Resolve SKU mapping
        resolved_sku = raw_sku
        if not resolved_sku:
            if raw_hsn and raw_hsn in hsn_map:
                resolved_sku = hsn_map[raw_hsn]
            elif raw_desc and raw_desc.lower() in desc_map:
                resolved_sku = desc_map[raw_desc.lower()]

        if not resolved_sku or resolved_sku not in product_map:
            unmapped_rows.append({
                "row_number": row_num,
                "invoice_no": raw_inv,
                "hsn_code": raw_hsn,
                "item_description": raw_desc,
                "quantity": qty_val,
                "reason": f"Unmapped item: SKU '{resolved_sku or 'empty'}' / HSN '{raw_hsn}' not matched to store catalog"
            })
            continue

        prod = product_map[resolved_sku]
        valid_rows.append({
            "row_number": row_num,
            "invoice_no": raw_inv,
            "invoice_date": date_clean,
            "supply_type": norm_type,
            "gstin_counterparty": raw_gstin,
            "hsn_code": raw_hsn,
            "item_description": raw_desc or prod["name"],
            "sku": resolved_sku,
            "product_id": prod["id"],
            "product_name": prod["name"],
            "quantity": int(qty_val),
            "taxable_value": raw_tax,
            "gst_rate": raw_rate,
            "total_value": raw_val
        })

    return {
        "batch_id": batch_id,
        "filename": filename,
        "total_rows": len(valid_rows) + len(invalid_rows) + len(unmapped_rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "unmapped_count": len(unmapped_rows),
        "is_valid": len(valid_rows) > 0,
        "preview_valid": valid_rows[:25],
        "all_valid": valid_rows,
        "invalid_rows": invalid_rows,
        "unmapped_rows": unmapped_rows
    }

def commit_gst_import(batch_id: str, filename: str, valid_rows: List[Dict[str, Any]], shop_id: int = 1, update_stock: bool = True) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    if not valid_rows:
        return {"status": "error", "message": "No valid GST records to import."}

    # Record batch
    cursor.execute("""
        INSERT INTO import_batches (id, filename, batch_type, total_rows, valid_rows, invalid_rows, status)
        VALUES (?, ?, 'GST', ?, ?, 0, 'COMPLETED')
    """, (batch_id, filename, len(valid_rows), len(valid_rows)))

    outward_sales = 0
    inward_receipts = 0

    for r in valid_rows:
        # Insert GST line
        cursor.execute("""
            INSERT INTO gst_lines (
                shop_id, invoice_no, invoice_date, supply_type, gstin_counterparty,
                hsn_code, item_description, sku, quantity, taxable_value, gst_rate,
                total_value, import_batch_id, is_mapped
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            shop_id, r["invoice_no"], r["invoice_date"], r["supply_type"], r.get("gstin_counterparty"),
            r.get("hsn_code"), r.get("item_description"), r["sku"], r["quantity"],
            r.get("taxable_value", 0), r.get("gst_rate", 0), r.get("total_value", 0), batch_id
        ))

        if r["supply_type"] == "outward":
            # Outward supply converts into sales history for demand forecasting
            cursor.execute("""
                INSERT OR IGNORE INTO sales (shop_id, product_id, sku, sale_date, quantity_sold, source, import_batch_id)
                VALUES (?, ?, ?, ?, ?, 'GST_OUTWARD', ?)
            """, (shop_id, r["product_id"], r["sku"], r["invoice_date"], int(r["quantity"]), batch_id))
            outward_sales += 1
        elif r["supply_type"] == "inward" and update_stock:
            # Inward supply updates stock position via inventory movement
            qty = int(r["quantity"])
            cursor.execute("UPDATE products SET current_stock = current_stock + ? WHERE id = ?", (qty, r["product_id"]))
            cursor.execute("SELECT current_stock FROM products WHERE id = ?", (r["product_id"],))
            new_bal = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO inventory_movements (shop_id, product_id, movement_type, quantity, balance_after, reason)
                VALUES (?, ?, 'GST_INWARD', ?, ?, ?)
            """, (shop_id, r["product_id"], qty, new_bal, f"GST Inward Invoice {r['invoice_no']}"))
            inward_receipts += 1

    db.commit()
    return {
        "status": "success",
        "batch_id": batch_id,
        "imported_count": len(valid_rows),
        "outward_sales_added": outward_sales,
        "inward_receipts_recorded": inward_receipts,
        "message": f"Successfully ingested {len(valid_rows)} GST invoice lines ({outward_sales} sales transactions, {inward_receipts} inventory receipts)."
    }
