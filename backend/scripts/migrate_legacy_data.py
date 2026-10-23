import sys
import os
import sqlite3
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from backend.config import Config
from backend.database import get_standalone_db, init_db
from backend.utils.money import rupees_to_paise

def migrate_data(dry_run: bool = False):
    """
    One-time migration script migrating existing legacy schema and data
    into the updated SQLite architecture with integer paise and inventory table.
    """
    db_file = Path(Config.DATABASE)
    print(f"[{'DRY-RUN' if dry_run else 'EXECUTE'}] Checking database: {db_file}")

    if not db_file.exists():
        print(f"Database {db_file} does not exist yet. Initializing new schema...")
        if not dry_run:
            init_db()
        return

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Inspect existing products
    cursor.execute("PRAGMA table_info(products)")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    print(f"[Audit] Existing products columns: {sorted(list(existing_cols))}")

    missing_cols = []
    if "unit" not in existing_cols:
        missing_cols.append(("unit", "TEXT DEFAULT 'unit'"))
    if "barcode" not in existing_cols:
        missing_cols.append(("barcode", "TEXT"))
    if "gst_rate" not in existing_cols:
        missing_cols.append(("gst_rate", "REAL DEFAULT 0.0"))
    if "retail_price_paise" not in existing_cols:
        missing_cols.append(("retail_price_paise", "INTEGER DEFAULT 0"))
    if "unit_cost_paise" not in existing_cols:
        missing_cols.append(("unit_cost_paise", "INTEGER DEFAULT 0"))

    if missing_cols:
        print(f"[Migration] Need to add missing columns to products: {[col[0] for col in missing_cols]}")
        if not dry_run:
            for col_name, col_def in missing_cols:
                try:
                    cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_def}")
                    print(f"  + Added column {col_name} to products")
                except Exception as e:
                    print(f"  - Column {col_name} addition skipped or failed: {e}")
            conn.commit()

    # Reconcile inventory_movements columns
    cursor.execute("PRAGMA table_info(inventory_movements)")
    im_cols = {row["name"] for row in cursor.fetchall()}
    im_missing = []
    if "owner_id" not in im_cols:
        im_missing.append(("owner_id", "INTEGER DEFAULT 1 REFERENCES users(id)"))
    if "delta" not in im_cols:
        im_missing.append(("delta", "INTEGER DEFAULT 0"))
    if "reference" not in im_cols:
        im_missing.append(("reference", "TEXT"))
    if "created_at" not in im_cols:
        im_missing.append(("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

    if im_missing:
        print(f"[Migration] Need to add missing columns to inventory_movements: {[c[0] for c in im_missing]}")
        if not dry_run:
            for col_name, col_def in im_missing:
                try:
                    cursor.execute(f"ALTER TABLE inventory_movements ADD COLUMN {col_name} {col_def}")
                    print(f"  + Added column {col_name} to inventory_movements")
                except Exception as e:
                    print(f"  - Column {col_name} addition skipped or failed: {e}")
            conn.commit()

    # Reconcile sales columns
    cursor.execute("PRAGMA table_info(sales)")
    sales_cols = {row["name"] for row in cursor.fetchall()}
    sales_missing = []
    if "owner_id" not in sales_cols:
        sales_missing.append(("owner_id", "INTEGER DEFAULT 1 REFERENCES users(id)"))
    if "utr" not in sales_cols:
        sales_missing.append(("utr", "TEXT"))
    if "subtotal_paise" not in sales_cols:
        sales_missing.append(("subtotal_paise", "INTEGER DEFAULT 0"))
    if "tax_paise" not in sales_cols:
        sales_missing.append(("tax_paise", "INTEGER DEFAULT 0"))
    if "total_paise" not in sales_cols:
        sales_missing.append(("total_paise", "INTEGER DEFAULT 0"))
    if "payment_status" not in sales_cols:
        sales_missing.append(("payment_status", "TEXT DEFAULT 'PAID'"))

    if sales_missing:
        print(f"[Migration] Need to add missing columns to sales: {[c[0] for c in sales_missing]}")
        if not dry_run:
            for col_name, col_def in sales_missing:
                try:
                    cursor.execute(f"ALTER TABLE sales ADD COLUMN {col_name} {col_def}")
                    print(f"  + Added column {col_name} to sales")
                except Exception as e:
                    print(f"  - Column {col_name} addition skipped or failed: {e}")
            conn.commit()

    # 2. Backfill integer paise from selling_price / unit_cost
    cursor.execute("SELECT id, sku, selling_price, unit_cost, current_stock FROM products")
    products = cursor.fetchall()
    print(f"[Audit] Found {len(products)} products in catalog.")

    if not dry_run:
        for p in products:
            rp_paise = rupees_to_paise(p["selling_price"] or 0)
            uc_paise = rupees_to_paise(p["unit_cost"] or 0)
            cursor.execute("""
                UPDATE products 
                SET retail_price_paise = ?, unit_cost_paise = ? 
                WHERE id = ?
            """, (rp_paise, uc_paise, p["id"]))
        conn.commit()
        print(f"[Migration] Backfilled integer paise for {len(products)} products.")

    # 3. Ensure new tables exist via init_db
    if not dry_run:
        init_db(drop_all=False)
        print("[Migration] Verified all SQLAlchemy ORM tables are created.")

    # 4. Migrate stock into `inventory` table
    cursor.execute("SELECT COUNT(*) FROM inventory")
    existing_inv_count = cursor.fetchone()[0]
    print(f"[Audit] Current inventory table count: {existing_inv_count}")

    if not dry_run and existing_inv_count == 0:
        inserted_inv = 0
        for p in products:
            stock = max(0, int(p["current_stock"] or 0))
            cursor.execute("""
                INSERT OR IGNORE INTO inventory (product_id, owner_id, on_hand, reorder_level)
                VALUES (?, 1, ?, 10)
            """, (p["id"], stock))
            inserted_inv += 1
        conn.commit()
        print(f"[Migration] Populated inventory table with {inserted_inv} product positions.")

    # 5. Summary counts
    counts = {}
    for table in [
        "users", "products", "inventory", "sales", "purchase_orders", 
        "inventory_movements", "alerts", "scan_sessions", "detection_events"
    ]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except Exception:
            counts[table] = "N/A"

    print("\n[Report] Current Database Entity Counts:")
    for tbl, cnt in counts.items():
        print(f"  - {tbl:20}: {cnt}")

    conn.close()
    print(f"[{'DRY-RUN' if dry_run else 'SUCCESS'}] Data migration finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StockSense AI Data Migration")
    parser.add_argument("--dry-run", action="store_true", help="Print migration plan without writing changes")
    args = parser.parse_args()
    migrate_data(dry_run=args.dry_run)
