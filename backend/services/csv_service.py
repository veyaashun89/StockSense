import csv
import io
import uuid
import datetime
from typing import Dict, Any, List, Tuple
from backend.database import get_db

def validate_and_preview_sales_csv(file_content: str, filename: str) -> Dict[str, Any]:
    """
    Validates CSV structure and rows without committing to database.
    Returns preview data, valid count, invalid count, errors list.
    """
    db = get_db()
    cursor = db.cursor()

    # Fetch existing active SKUs and their product IDs
    cursor.execute("SELECT sku, id FROM products WHERE is_active = 1")
    product_map = {row["sku"].upper(): row["id"] for row in cursor.fetchall()}

    # Check for empty content
    if not file_content or not file_content.strip():
        return {
            "batch_id": None,
            "filename": filename,
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "duplicate_count": 0,
            "is_valid": False,
            "error": "The uploaded CSV file is empty.",
            "valid_rows": [],
            "invalid_rows": []
        }

    # Normalize line endings
    reader = csv.reader(io.StringIO(file_content.strip()))
    try:
        headers = [h.strip().lower() for h in next(reader, [])]
    except Exception as e:
        return {
            "batch_id": None,
            "filename": filename,
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "duplicate_count": 0,
            "is_valid": False,
            "error": f"Failed to parse CSV header: {str(e)}",
            "valid_rows": [],
            "invalid_rows": []
        }

    required_cols = {"sku", "sale_date", "quantity_sold"}
    missing_cols = required_cols - set(headers)
    if missing_cols:
        return {
            "batch_id": None,
            "filename": filename,
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "duplicate_count": 0,
            "is_valid": False,
            "error": f"Missing required column(s): {', '.join(sorted(missing_cols))}. Expected headers: sku,sale_date,quantity_sold",
            "valid_rows": [],
            "invalid_rows": []
        }

    sku_idx = headers.index("sku")
    date_idx = headers.index("sale_date")
    qty_idx = headers.index("quantity_sold")

    valid_rows = []
    invalid_rows = []
    seen_in_batch = set()
    batch_id = str(uuid.uuid4())

    row_num = 1  # 1-indexed header is row 1
    for row in reader:
        row_num += 1
        if not row or not any(field.strip() for field in row):
            continue  # skip completely blank lines

        if len(row) <= max(sku_idx, date_idx, qty_idx):
            invalid_rows.append({
                "row_number": row_num,
                "raw_data": ",".join(row),
                "reason": "Row has fewer columns than header"
            })
            continue

        raw_sku = row[sku_idx].strip()
        raw_date = row[date_idx].strip()
        raw_qty = row[qty_idx].strip()

        # Validate SKU
        sku_clean = raw_sku.upper()
        if not sku_clean:
            invalid_rows.append({
                "row_number": row_num,
                "raw_data": f"{raw_sku},{raw_date},{raw_qty}",
                "reason": "SKU cannot be empty"
            })
            continue

        if sku_clean not in product_map:
            invalid_rows.append({
                "row_number": row_num,
                "raw_data": f"{raw_sku},{raw_date},{raw_qty}",
                "reason": f"Unknown SKU '{raw_sku}'. Product does not exist in inventory."
            })
            continue

        # Validate Date
        try:
            parsed_date = datetime.date.fromisoformat(raw_date)
            date_clean = parsed_date.isoformat()
        except Exception:
            invalid_rows.append({
                "row_number": row_num,
                "raw_data": f"{raw_sku},{raw_date},{raw_qty}",
                "reason": f"Invalid date format '{raw_date}'. Must be YYYY-MM-DD."
            })
            continue

        # Validate Quantity
        try:
            qty_int = int(raw_qty)
            if qty_int <= 0:
                invalid_rows.append({
                    "row_number": row_num,
                    "raw_data": f"{raw_sku},{raw_date},{raw_qty}",
                    "reason": f"Quantity must be a positive integer, got '{raw_qty}'"
                })
                continue
        except ValueError:
            invalid_rows.append({
                "row_number": row_num,
                "raw_data": f"{raw_sku},{raw_date},{raw_qty}",
                "reason": f"Quantity '{raw_qty}' is not a valid integer"
            })
            continue

        # Deduplication check within file
        dedup_key = (sku_clean, date_clean)
        if dedup_key in seen_in_batch:
            invalid_rows.append({
                "row_number": row_num,
                "raw_data": f"{raw_sku},{raw_date},{raw_qty}",
                "reason": f"Duplicate record for SKU {sku_clean} on {date_clean} within the same file"
            })
            continue
        seen_in_batch.add(dedup_key)

        valid_rows.append({
            "row_number": row_num,
            "product_id": product_map[sku_clean],
            "sku": sku_clean,
            "sale_date": date_clean,
            "quantity_sold": qty_int
        })

    # Check for existing sales in database for warning/conflict
    cursor.execute("SELECT sku, sale_date FROM sales")
    existing_in_db = set((row[0], row[1]) for row in cursor.fetchall())
    
    db_duplicate_count = 0
    final_valid_rows = []
    for r in valid_rows:
        if (r["sku"], r["sale_date"]) in existing_in_db:
            db_duplicate_count += 1
            invalid_rows.append({
                "row_number": r["row_number"],
                "raw_data": f"{r['sku']},{r['sale_date']},{r['quantity_sold']}",
                "reason": f"Record already exists in database for SKU {r['sku']} on {r['sale_date']} (Ignored to prevent double counting)"
            })
        else:
            final_valid_rows.append(r)

    total_evaluated = len(final_valid_rows) + len(invalid_rows)
    return {
        "batch_id": batch_id,
        "filename": filename,
        "total_rows": total_evaluated,
        "valid_count": len(final_valid_rows),
        "invalid_count": len(invalid_rows),
        "duplicate_count": db_duplicate_count,
        "is_valid": len(final_valid_rows) > 0,
        "preview_valid": final_valid_rows[:25],
        "all_valid": final_valid_rows,
        "invalid_rows": invalid_rows
    }

def commit_sales_import(batch_id: str, filename: str, valid_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Saves validated rows to database inside an atomic transaction.
    """
    db = get_db()
    cursor = db.cursor()

    if not valid_records:
        return {"status": "error", "message": "No valid records to import."}

    # Record batch
    cursor.execute("""
        INSERT INTO import_batches (id, filename, total_rows, valid_rows, invalid_rows, status)
        VALUES (?, ?, ?, ?, ?, 'COMPLETED')
    """, (batch_id, filename, len(valid_records), len(valid_records), 0))

    # Insert sales records
    insert_data = [
        (r["product_id"], r["sku"], r["sale_date"], r["quantity_sold"], batch_id)
        for r in valid_records
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO sales (product_id, sku, sale_date, quantity_sold, import_batch_id)
        VALUES (?, ?, ?, ?, ?)
    """, insert_data)

    db.commit()
    return {
        "status": "success",
        "batch_id": batch_id,
        "imported_count": len(insert_data),
        "message": f"Successfully imported {len(insert_data)} sales records."
    }

def import_products_csv(file_content: str) -> Dict[str, Any]:
    """
    Imports or updates products from a standard CSV.
    Headers: sku,name,category,current_stock,unit_cost,selling_price,lead_time_days,is_perishable,shelf_life_days,min_order_qty,pack_size,safety_buffer_days
    """
    db = get_db()
    cursor = db.cursor()

    reader = csv.reader(io.StringIO(file_content.strip()))
    headers = [h.strip().lower() for h in next(reader, [])]

    if "sku" not in headers or "name" not in headers or "category" not in headers:
        raise ValueError("CSV must contain at least 'sku', 'name', and 'category' columns.")

    sku_idx = headers.index("sku")
    name_idx = headers.index("name")
    cat_idx = headers.index("category")
    stock_idx = headers.index("current_stock") if "current_stock" in headers else None
    cost_idx = headers.index("unit_cost") if "unit_cost" in headers else None
    price_idx = headers.index("selling_price") if "selling_price" in headers else None
    lead_idx = headers.index("lead_time_days") if "lead_time_days" in headers else None
    perish_idx = headers.index("is_perishable") if "is_perishable" in headers else None
    shelf_idx = headers.index("shelf_life_days") if "shelf_life_days" in headers else None
    moq_idx = headers.index("min_order_qty") if "min_order_qty" in headers else None
    pack_idx = headers.index("pack_size") if "pack_size" in headers else None
    buff_idx = headers.index("safety_buffer_days") if "safety_buffer_days" in headers else None

    inserted = 0
    updated = 0

    for row in reader:
        if not row or not any(field.strip() for field in row):
            continue
        sku = row[sku_idx].strip().upper()
        name = row[name_idx].strip()
        category = row[cat_idx].strip()
        stock = int(row[stock_idx].strip()) if stock_idx is not None and row[stock_idx].strip() else 0
        cost = float(row[cost_idx].strip()) if cost_idx is not None and row[cost_idx].strip() else 0.0
        price = float(row[price_idx].strip()) if price_idx is not None and row[price_idx].strip() else 0.0
        lead = int(row[lead_idx].strip()) if lead_idx is not None and row[lead_idx].strip() else 7
        perish = 1 if perish_idx is not None and row[perish_idx].strip().lower() in ("1", "true", "yes") else 0
        shelf = int(row[shelf_idx].strip()) if shelf_idx is not None and row[shelf_idx].strip() else None
        moq = int(row[moq_idx].strip()) if moq_idx is not None and row[moq_idx].strip() else 1
        pack = int(row[pack_idx].strip()) if pack_idx is not None and row[pack_idx].strip() else 1
        buff = int(row[buff_idx].strip()) if buff_idx is not None and row[buff_idx].strip() else 3

        cursor.execute("SELECT id FROM products WHERE sku = ?", (sku,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE products SET
                    name = ?, category = ?, current_stock = ?, unit_cost = ?,
                    selling_price = ?, lead_time_days = ?, is_perishable = ?,
                    shelf_life_days = ?, min_order_qty = ?, pack_size = ?,
                    safety_buffer_days = ?, is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (name, category, stock, cost, price, lead, perish, shelf, moq, pack, buff, existing["id"]))
            updated += 1
        else:
            cursor.execute("""
                INSERT INTO products (
                    sku, name, category, current_stock, unit_cost, selling_price,
                    lead_time_days, is_perishable, shelf_life_days, min_order_qty,
                    pack_size, safety_buffer_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, category, stock, cost, price, lead, perish, shelf, moq, pack, buff))
            inserted += 1

    db.commit()
    return {"status": "success", "inserted": inserted, "updated": updated}
