"""
StockSense AI - Open Food Facts (ODbL) Product Importer & Cache
--------------------------------------------------------------
Queries Open Food Facts API v0 by barcode (EAN-13, UPC-A), caches responses
in local SQLite storage, enforces rate limits, and maps fields into StockSense catalog.
Provides CSV fallback import for team-entered products.

Licence Attribution:
Data and images are sourced from Open Food Facts under the Open Database License (ODbL).
Individual images may be licensed under Creative Commons.
See: https://world.openfoodfacts.org
"""

import time
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from backend.database import get_db

logger = logging.getLogger(__name__)

USER_AGENT = "StockSenseAI/2.0 (veyaashun89; https://github.com/veyaashun89/StockSense)"
OFF_API_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
LAST_REQUEST_TIME = 0.0
MIN_REQUEST_INTERVAL = 1.0  # Respect Open Food Facts rate limit (1 req/sec)

def init_off_cache_table():
    """Ensures local SQLite cache table exists for Open Food Facts queries."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS open_food_facts_cache (
            barcode TEXT PRIMARY KEY,
            product_name TEXT,
            brand TEXT,
            category TEXT,
            image_url TEXT,
            raw_json TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

def query_open_food_facts(barcode: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Queries Open Food Facts for a product by barcode (EAN-13).
    Checks local SQLite cache first. If cache miss, requests remote API with rate limiting.
    """
    global LAST_REQUEST_TIME
    clean_barcode = str(barcode).strip()
    if not clean_barcode:
        return None

    init_off_cache_table()
    db = get_db()
    cursor = db.cursor()

    # 1. Check local cache
    if use_cache:
        cursor.execute("SELECT * FROM open_food_facts_cache WHERE barcode = ?", (clean_barcode,))
        row = cursor.fetchone()
        if row:
            try:
                cached_data = json.loads(row["raw_json"])
                cached_data["_cached"] = True
                cached_data["_cached_at"] = row["cached_at"]
                return cached_data
            except Exception:
                pass

    # 2. Rate-limit guard
    now = time.time()
    elapsed = now - LAST_REQUEST_TIME
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    LAST_REQUEST_TIME = time.time()

    # 3. Query Open Food Facts API
    url = OFF_API_URL.format(barcode=clean_barcode)
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, timeout=6.0)
        if resp.status_code != 200:
            logger.warning(f"Open Food Facts API returned HTTP {resp.status_code} for {clean_barcode}")
            return None

        data = resp.json()
        if data.get("status") != 1 or "product" not in data:
            return None

        prod_data = data["product"]
        name = prod_data.get("product_name") or prod_data.get("product_name_en") or clean_barcode
        brand = prod_data.get("brands") or "Generic"
        category = prod_data.get("categories") or "Packaged Foods"
        if "," in category:
            category = category.split(",")[0].strip()
        image_url = prod_data.get("image_url") or prod_data.get("image_front_url") or ""

        normalized = {
            "barcode": clean_barcode,
            "sku": f"SKU-OFF-{clean_barcode[-6:]}",
            "name": name,
            "brand": brand,
            "category": category,
            "image_url": image_url,
            "data_source": "Open Food Facts (ODbL)",
            "attribution": "Data from Open Food Facts contributors under ODbL"
        }

        # 4. Cache response
        cursor.execute("""
            INSERT OR REPLACE INTO open_food_facts_cache (barcode, product_name, brand, category, image_url, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (clean_barcode, name, brand, category, image_url, json.dumps(normalized)))
        db.commit()

        normalized["_cached"] = False
        return normalized

    except Exception as e:
        logger.error(f"Error querying Open Food Facts for {clean_barcode}: {e}")
        return None

def import_off_product_to_catalog(
    barcode: str,
    shop_id: int = 1,
    unit_cost_paise: int = 3000,
    retail_price_paise: int = 4500,
    initial_stock: int = 50
) -> Dict[str, Any]:
    """
    Fetches product from Open Food Facts and persists it into the products and inventory tables.
    """
    prod = query_open_food_facts(barcode)
    if not prod:
        raise ValueError(f"Product with barcode '{barcode}' not found in Open Food Facts.")

    db = get_db()
    cursor = db.cursor()

    sku = prod["sku"]
    name = prod["name"]
    category = prod["category"]
    brand = prod["brand"]
    image_url = prod["image_url"]

    # Insert or update in products table
    cursor.execute("""
        INSERT INTO products (
            shop_id, sku, name, category, unit, unit_cost_paise, retail_price_paise,
            selling_price, unit_cost, barcode, is_active
        ) VALUES (?, ?, ?, ?, 'unit', ?, ?, ?, ?, ?, 1)
        ON CONFLICT(sku) DO UPDATE SET
            name = excluded.name,
            category = excluded.category,
            barcode = excluded.barcode,
            retail_price_paise = excluded.retail_price_paise,
            unit_cost_paise = excluded.unit_cost_paise,
            is_active = 1
    """, (
        shop_id, sku, f"{brand} {name}".strip(), category,
        unit_cost_paise, retail_price_paise,
        retail_price_paise / 100.0, unit_cost_paise / 100.0,
        barcode
    ))
    db.commit()

    # Get product ID
    cursor.execute("SELECT id FROM products WHERE sku = ?", (sku,))
    prod_id = cursor.fetchone()[0]

    # Initialize inventory row and record audit movement
    cursor.execute("""
        INSERT INTO inventory (product_id, owner_id, on_hand, reorder_level)
        VALUES (?, ?, ?, 15)
        ON CONFLICT(product_id, owner_id) DO UPDATE SET
            on_hand = excluded.on_hand
    """, (prod_id, 1, initial_stock))

    # Update cached counter on products
    cursor.execute("UPDATE products SET current_stock = ? WHERE id = ?", (initial_stock, prod_id))

    # Rule 5 audit log
    cursor.execute("""
        INSERT INTO inventory_movements (shop_id, product_id, owner_id, delta, quantity, movement_type, balance_after, reason, reference)
        VALUES (1, ?, 1, ?, ?, 'IMPORT', ?, 'IMPORT', ?)
    """, (prod_id, initial_stock, initial_stock, initial_stock, f"Open Food Facts Inward: {barcode}"))
    db.commit()

    return {
        "status": "success",
        "product_id": prod_id,
        "sku": sku,
        "name": f"{brand} {name}".strip(),
        "barcode": barcode,
        "category": category,
        "image_url": image_url,
        "stock": initial_stock,
        "retail_price_paise": retail_price_paise,
        "source": "Open Food Facts (ODbL)"
    }

def import_products_from_csv(csv_content: str, shop_id: int = 1) -> Dict[str, Any]:
    """
    CSV Fallback importer for team-entered or offline products.
    Expected CSV columns: barcode, sku, name, brand, category, unit_cost_paise, retail_price_paise, initial_stock
    """
    import csv
    import io

    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    imported = []
    errors = []

    db = get_db()
    cursor = db.cursor()

    for idx, row in enumerate(reader, start=1):
        try:
            barcode = (row.get("barcode") or "").strip()
            sku = (row.get("sku") or f"SKU-{barcode}").strip()
            name = (row.get("name") or "Unnamed Product").strip()
            brand = (row.get("brand") or "").strip()
            category = (row.get("category") or "General").strip()
            cost_paise = int(row.get("unit_cost_paise") or 2500)
            price_paise = int(row.get("retail_price_paise") or 3500)
            stock = int(row.get("initial_stock") or 20)

            full_name = f"{brand} {name}".strip() if brand else name

            cursor.execute("""
                INSERT INTO products (
                    shop_id, sku, name, category, unit, unit_cost_paise, retail_price_paise,
                    selling_price, unit_cost, barcode, is_active
                ) VALUES (?, ?, ?, ?, 'unit', ?, ?, ?, ?, ?, 1)
                ON CONFLICT(sku) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    barcode = excluded.barcode,
                    unit_cost_paise = excluded.unit_cost_paise,
                    retail_price_paise = excluded.retail_price_paise
            """, (
                shop_id, sku, full_name, category, cost_paise, price_paise,
                price_paise / 100.0, cost_paise / 100.0, barcode
            ))

            cursor.execute("SELECT id FROM products WHERE sku = ?", (sku,))
            pid = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO inventory (product_id, owner_id, on_hand, reorder_level)
                VALUES (?, 1, ?, 10)
                ON CONFLICT(product_id, owner_id) DO UPDATE SET on_hand = excluded.on_hand
            """, (pid, stock))
            cursor.execute("UPDATE products SET current_stock = ? WHERE id = ?", (stock, pid))

            cursor.execute("""
                INSERT INTO inventory_movements (shop_id, product_id, owner_id, delta, quantity, movement_type, balance_after, reason, reference)
                VALUES (1, ?, 1, ?, ?, 'IMPORT', ?, 'IMPORT', ?)
            """, (pid, stock, stock, stock, f"Team CSV Import: {sku}"))

            imported.append({"sku": sku, "name": full_name, "barcode": barcode, "stock": stock})
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")

    db.commit()
    return {
        "status": "success",
        "imported_count": len(imported),
        "error_count": len(errors),
        "imported": imported,
        "errors": errors,
        "source": "Team CSV Fallback"
    }
