import datetime
import random
from pathlib import Path
from typing import Dict, Any
from backend.database import get_db, init_db
from backend.services.alert_service import evaluate_and_generate_alerts

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"

def seed_demonstration_data(reset: bool = True) -> Dict[str, Any]:
    if reset:
        init_db(drop_all=True)

    db = get_db()
    cursor = db.cursor()

    # 1. Suppliers
    suppliers = [
        ("FreshValley Dairy Co.", 2, 24, 12, "orders@freshvalleydairy.com"),
        ("Golden Grain Millers", 5, 10, 5, "supply@goldengrain.com"),
        ("Prime Staples & Pantry Ltd.", 7, 24, 12, "wholesale@primestaples.com"),
        ("Artisan Beverage Distributors", 3, 12, 6, "sales@artisanbev.com"),
        ("CleanHome Consumer Goods", 7, 20, 10, "orders@cleanhome.com"),
        ("SlowBoat Global Logistics", 10, 50, 25, "incompatible@slowboat.com") # Lead time exceeds shelf life demo!
    ]
    cursor.executemany("""
        INSERT INTO suppliers (name, lead_time, min_order_qty, pack_size, contact_email)
        VALUES (?, ?, ?, ?, ?)
    """, suppliers)

    cursor.execute("SELECT id, name FROM suppliers")
    sup_map = {row["name"]: row["id"] for row in cursor.fetchall()}

    # 2. Products Catalog (30 products covering all required behaviors)
    # sku, name, category, current_stock, unit_cost, selling_price, supplier, lead_time, is_perishable, shelf_life, min_order, pack_size, safety_buffer
    products_data = [
        # Dairy & Fresh (Perishable)
        ("SKU-MLK-01", "Fresh Whole Milk 1 Gal", "Dairy & Fresh", 8, 2.40, 4.29, "FreshValley Dairy Co.", 2, 1, 7, 24, 6, 2),
        ("SKU-YOG-02", "Greek Yogurt Plain 32oz", "Dairy & Fresh", 45, 2.10, 3.99, "FreshValley Dairy Co.", 3, 1, 14, 12, 6, 3),
        ("SKU-EGG-03", "Farm Fresh Grade A Eggs 12pk", "Dairy & Fresh", 14, 1.80, 3.49, "FreshValley Dairy Co.", 2, 1, 21, 24, 12, 2),
        ("SKU-CHS-04", "Organic Cheddar Cheese 200g", "Dairy & Fresh", 28, 2.90, 5.29, "FreshValley Dairy Co.", 4, 1, 35, 12, 6, 3),
        ("SKU-BTR-05", "Sweet Cream Butter 454g", "Dairy & Fresh", 19, 2.60, 4.89, "FreshValley Dairy Co.", 3, 1, 45, 12, 6, 3),
        ("SKU-BER-06", "Organic Fresh Strawberries 400g", "Dairy & Fresh", 3, 3.10, 5.99, "FreshValley Dairy Co.", 2, 1, 5, 10, 5, 1), # Shelf life cap binding!

        # Incompatible Shelf Life Demonstration Item
        ("SKU-SUS-07", "Fresh Raw Tuna Sushi Grade 250g", "Dairy & Fresh", 0, 8.50, 16.99, "SlowBoat Global Logistics", 10, 1, 4, 10, 5, 1), # Lead time 10d > Shelf life 4d!

        # Bakery & Staples
        ("SKU-BRD-08", "Artisan Sourdough Loaf 500g", "Bakery & Staples", 2, 1.50, 3.99, "Golden Grain Millers", 1, 1, 4, 10, 5, 1),
        ("SKU-RIC-09", "Royal Basmati Rice 5kg", "Bakery & Staples", 65, 7.50, 12.99, "Golden Grain Millers", 6, 0, None, 10, 5, 4),
        ("SKU-FLR-10", "Unbleached Bread Flour 2kg", "Bakery & Staples", 18, 1.90, 3.79, "Golden Grain Millers", 5, 0, None, 15, 5, 3),
        ("SKU-PST-11", "Bronze Cut Penne Pasta 500g", "Bakery & Staples", 35, 0.95, 2.29, "Golden Grain Millers", 5, 0, None, 24, 12, 3),
        ("SKU-SGR-12", "Pure Cane Granulated Sugar 2kg", "Bakery & Staples", 40, 1.80, 3.49, "Golden Grain Millers", 4, 0, None, 10, 5, 3),
        ("SKU-BAG-13", "Plain New York Bagels 6pk", "Bakery & Staples", 6, 2.20, 4.49, "Golden Grain Millers", 2, 1, 6, 12, 6, 2),

        # Packaged Foods
        ("SKU-TOM-14", "San Marzano Diced Tomatoes 400g", "Packaged Foods", 22, 1.10, 2.49, "Prime Staples & Pantry Ltd.", 7, 0, None, 48, 24, 4),
        ("SKU-OIL-15", "Extra Virgin Olive Oil 750ml", "Packaged Foods", 9, 6.20, 11.99, "Prime Staples & Pantry Ltd.", 8, 0, None, 12, 6, 4),
        ("SKU-PNT-16", "Creamy Organic Peanut Butter 500g", "Packaged Foods", 26, 2.50, 4.99, "Prime Staples & Pantry Ltd.", 6, 0, None, 12, 6, 3),
        ("SKU-OAT-17", "Whole Rolled Oats 1kg", "Packaged Foods", 30, 2.00, 3.99, "Prime Staples & Pantry Ltd.", 5, 0, None, 12, 6, 3),
        ("SKU-TNA-18", "Albacore Solid White Tuna 150g", "Packaged Foods", 55, 1.40, 2.99, "Prime Staples & Pantry Ltd.", 7, 0, None, 24, 12, 3),
        ("SKU-SOUP-19","Organic Minestrone Soup 500ml", "Packaged Foods", 40, 1.80, 3.79, "Prime Staples & Pantry Ltd.", 5, 0, None, 12, 6, 3),

        # Beverages
        ("SKU-COF-20", "Signature Dark Roast Coffee 400g", "Beverages", 12, 5.50, 10.99, "Artisan Beverage Distributors", 5, 0, None, 10, 5, 3),
        ("SKU-OJ-21",  "Cold Pressed Orange Juice 1L", "Beverages", 6, 2.80, 5.49, "Artisan Beverage Distributors", 2, 1, 10, 12, 6, 2),
        ("SKU-TEA-22", "Organic Green Tea Bags 50pk", "Beverages", 32, 2.20, 4.79, "Artisan Beverage Distributors", 4, 0, None, 12, 6, 3),
        ("SKU-WTR-23", "Sparkling Spring Water 1L", "Beverages", 48, 0.70, 1.89, "Artisan Beverage Distributors", 3, 0, None, 24, 12, 2),
        ("SKU-ALM-24", "Unsweetened Almond Milk 1L", "Beverages", 16, 1.95, 3.89, "Artisan Beverage Distributors", 3, 1, 30, 12, 6, 2),

        # Household & Personal Care
        ("SKU-DSH-25", "Ultra Grease Dish Soap 500ml", "Household", 15, 1.60, 3.29, "CleanHome Consumer Goods", 6, 0, None, 20, 10, 3),
        ("SKU-DET-26", "Concentrated Laundry Detergent 2L", "Household", 42, 6.50, 12.99, "CleanHome Consumer Goods", 7, 0, None, 10, 5, 3),
        ("SKU-TOW-27", "2-Ply Kitchen Paper Towels 6pk", "Household", 0, 4.20, 8.49, "CleanHome Consumer Goods", 5, 0, None, 12, 6, 3), # Critical stockout!
        ("SKU-TP-28",  "Enamel Care Mint Toothpaste 120ml", "Personal Care", 24, 1.75, 3.99, "CleanHome Consumer Goods", 6, 0, None, 24, 12, 3),
        ("SKU-SOAP-29","Moisturizing Liquid Hand Soap 300ml", "Personal Care", 38, 1.30, 2.99, "CleanHome Consumer Goods", 4, 0, None, 20, 10, 3),
        ("SKU-SHP-30", "Gentle Botanical Shampoo 400ml", "Personal Care", 20, 3.50, 7.49, "CleanHome Consumer Goods", 6, 0, None, 12, 6, 3),
    ]

    for p in products_data:
        sku, name, cat, stock, cost, price, sup_name, lead, perish, shelf, moq, pack, buff = p
        sup_id = sup_map.get(sup_name)
        cost_paise = int(round(cost * 100))
        price_paise = int(round(price * 100))
        cursor.execute("""
            INSERT INTO products (
                shop_id, sku, name, category, unit, current_stock, unit_cost, selling_price,
                unit_cost_paise, retail_price_paise, gst_rate,
                supplier_id, lead_time_days, is_perishable, shelf_life_days,
                min_order_qty, pack_size, safety_buffer_days
            ) VALUES (1, ?, ?, ?, 'unit', ?, ?, ?, ?, ?, 5.0, ?, ?, ?, ?, ?, ?, ?)
        """, (sku, name, cat, stock, cost, price, cost_paise, price_paise, sup_id, lead, perish, shelf, moq, pack, buff))
        pid = cursor.lastrowid

        cursor.execute("""
            INSERT INTO inventory (product_id, owner_id, on_hand, reorder_level)
            VALUES (?, 1, ?, ?)
        """, (pid, stock, moq))

        cursor.execute("""
            INSERT INTO inventory_movements (shop_id, product_id, owner_id, movement_type, quantity, delta, balance_after, reason)
            VALUES (1, ?, 1, 'INITIAL', ?, ?, ?, 'Demo setup initialization')
        """, (pid, stock, stock, stock))

    # 3. Deterministic Historical Sales (60 Days)
    cursor.execute("SELECT id, sku FROM products WHERE shop_id = 1")
    products_db = cursor.fetchall()
    today = datetime.date.today()
    random.seed(42)

    demand_profiles = {
        "SKU-MLK-01": (14, 22),
        "SKU-YOG-02": (4, 9),
        "SKU-EGG-03": (8, 16),
        "SKU-CHS-04": (3, 7),
        "SKU-BTR-05": (2, 5),
        "SKU-BER-06": (5, 10),
        "SKU-SUS-07": (2, 4),
        "SKU-BRD-08": (12, 20),
        "SKU-RIC-09": (2, 4),
        "SKU-FLR-10": (3, 6),
        "SKU-PST-11": (5, 11),
        "SKU-SGR-12": (3, 6),
        "SKU-BAG-13": (4, 8),
        "SKU-TOM-14": (4, 9),
        "SKU-OIL-15": (1, 4),
        "SKU-PNT-16": (2, 5),
        "SKU-OAT-17": (2, 6),
        "SKU-TNA-18": (3, 7),
        "SKU-SOUP-19":(3, 6),
        "SKU-COF-20": (2, 5),
        "SKU-OJ-21":  (6, 12),
        "SKU-TEA-22": (2, 5),
        "SKU-WTR-23": (8, 15),
        "SKU-ALM-24": (3, 7),
        "SKU-DSH-25": (3, 6),
        "SKU-DET-26": (2, 4),
        "SKU-TOW-27": (4, 8),
        "SKU-TP-28":  (2, 5),
        "SKU-SOAP-29":(3, 6),
        "SKU-SHP-30": (2, 4)
    }

    sales_inserts = []
    total_sales = 0
    for day_offset in range(60, 0, -1):
        sale_date = today - datetime.timedelta(days=day_offset)
        weekend_mult = 1.35 if sale_date.weekday() in (5, 6) else 1.0

        for p in products_db:
            pid = p["id"]
            sku = p["sku"]
            min_q, max_q = demand_profiles.get(sku, (2, 5))
            if min_q <= 1 and random.random() < 0.2:
                continue
            base_q = random.randint(min_q, max_q)
            q = max(1, int(base_q * weekend_mult))
            sales_inserts.append((1, 1, pid, sku, sale_date.isoformat(), q, "MANUAL_OR_CSV", "DEMO-BATCH-001"))
            total_sales += 1

    cursor.executemany("""
        INSERT INTO sales (shop_id, owner_id, product_id, sku, sale_date, quantity_sold, source, import_batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sales_inserts)

    # 4. Stock Batches & Expiry Dates for Perishables
    cursor.execute("SELECT id, sku, current_stock, shelf_life_days FROM products WHERE is_perishable = 1 AND current_stock > 0")
    perishables = cursor.fetchall()
    for per in perishables:
        pid = per["id"]
        sku = per["sku"]
        stock = per["current_stock"]
        shelf = per["shelf_life_days"] or 7
        exp = (today + datetime.timedelta(days=max(1, shelf - 2))).isoformat()
        cursor.execute("""
            INSERT INTO stock_batches (shop_id, product_id, sku, batch_id, quantity, expiry_date)
            VALUES (1, ?, ?, ?, ?, ?)
        """, (pid, sku, f"LOT-{today.strftime('%Y%m')}-{pid}", stock, exp))

    # 5. Market Signals (Festival and Seasonality Index)
    market_signals = [
        (today.isoformat(), "category", "Dairy & Fresh", "festival_flag", 1.20, "Diwali / Festive Weekend Dairy Spike (+20%)"),
        (today.isoformat(), "category", "Bakery & Staples", "seasonality_index", 1.15, "Weekend household pantry restocking (+15%)"),
        (today.isoformat(), "sku", "SKU-MLK-01", "local_demand_index", 1.10, "Local festival morning demand multiplier")
    ]
    cursor.executemany("""
        INSERT INTO market_signals (date, scope_type, scope_value, signal_type, value, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, market_signals)

    # 6. Sample Wholesale Catalog (Wholesaler User ID = 2)
    wholesale_items = [
        (2, "SKU-MLK-01", "Fresh Whole Milk 1 Gal", "Dairy & Fresh", 2.25, 24, 6, 2, 7, 800),
        (2, "SKU-YOG-02", "Greek Yogurt Plain 32oz", "Dairy & Fresh", 1.95, 12, 6, 3, 14, 400),
        (2, "SKU-EGG-03", "Farm Fresh Grade A Eggs 12pk", "Dairy & Fresh", 1.65, 24, 12, 2, 21, 600),
        (2, "SKU-BRD-08", "Artisan Sourdough Loaf 500g", "Bakery & Staples", 1.35, 10, 5, 1, 4, 300),
        (2, "SKU-RIC-09", "Royal Basmati Rice 5kg", "Bakery & Staples", 7.00, 10, 5, 5, None, 250),
        (2, "SKU-TOW-27", "2-Ply Kitchen Paper Towels 6pk", "Household", 3.80, 12, 6, 4, None, 500)
    ]
    cursor.executemany("""
        INSERT INTO wholesale_catalog_items (
            wholesaler_id, sku, name, category, wholesale_price, moq, pack_size, lead_time_days, shelf_life_days, available_stock
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, wholesale_items)

    # 7. Sample Purchase Orders
    cursor.execute("""
        INSERT INTO purchase_orders (po_number, shop_id, wholesaler_id, status, total_amount, notes)
        VALUES ('PO-20261020-001', 1, 2, 'Delivered', 144.00, 'Prior delivery receipt')
    """)
    po1_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO purchase_order_items (po_id, product_id, sku, product_name, quantity, unit_cost, total_cost, received_quantity)
        VALUES (?, 1, 'SKU-MLK-01', 'Fresh Whole Milk 1 Gal', 60, 2.40, 144.00, 60)
    """, (po1_id,))

    cursor.execute("""
        INSERT INTO purchase_orders (po_number, shop_id, wholesaler_id, status, total_amount, notes)
        VALUES ('PO-20261023-002', 1, 2, 'Dispatched', 72.00, 'Pending arrival tomorrow (counts toward inventory position)')
    """)
    po2_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO purchase_order_items (po_id, product_id, sku, product_name, quantity, unit_cost, total_cost, received_quantity)
        VALUES (?, 1, 'SKU-MLK-01', 'Fresh Whole Milk 1 Gal', 30, 2.40, 72.00, 0)
    """, (po2_id,))

    # 8. Sample GST Mapping
    gst_mappings = [
        (1, "0401", "Fresh Milk", "SKU-MLK-01"),
        (1, "1905", "Bread Loaf", "SKU-BRD-08"),
        (1, "1006", "Basmati Rice", "SKU-RIC-09"),
        (1, "4818", "Paper Towels", "SKU-TOW-27")
    ]
    cursor.executemany("""
        INSERT INTO gst_mappings (shop_id, hsn_code, item_description, mapped_sku)
        VALUES (?, ?, ?, ?)
    """, gst_mappings)

    # 9. Evaluate Automated Alerts
    evaluate_and_generate_alerts(shop_id=1)

    # 10. Generate sample CSV files in sample_data/ for judges to test drag-and-drop
    SAMPLE_DIR.mkdir(exist_ok=True)

    # Sample GST Invoices CSV
    gst_csv_content = """invoice_no,invoice_date,supply_type,gstin_counterparty,hsn_code,item_description,sku,quantity,taxable_value,gst_rate,total_value
INV-2026-101,2026-10-22,outward,27AAAAA0000A1Z5,0401,Fresh Whole Milk 1 Gal,SKU-MLK-01,18,77.22,0,77.22
INV-2026-102,2026-10-22,outward,27AAAAA0000A1Z5,1905,Artisan Sourdough Loaf 500g,SKU-BRD-08,15,59.85,5,62.84
INV-2026-103,2026-10-22,inward,27BBBBB1111B1Z9,0401,Fresh Whole Milk 1 Gal,SKU-MLK-01,24,57.60,0,57.60
INV-2026-104,2026-10-22,outward,27AAAAA0000A1Z5,4818,Kitchen Paper Towels 6pk,SKU-TOW-27,8,67.92,12,76.07
INV-BAD-999,invalid-date,outward,INVALID_GSTIN,9999,Unknown Item Nonexistent,UNKNOWN_SKU,0,0,0,0
"""
    (SAMPLE_DIR / "gst_invoices.csv").write_text(gst_csv_content, encoding="utf-8")

    # Sample Stock CSV
    stock_csv_content = f"""sku,quantity_on_hand,as_of_date,batch_id,expiry_date
SKU-MLK-01,10,{today.isoformat()},LOT-M101,{(today + datetime.timedelta(days=6)).isoformat()}
SKU-YOG-02,40,{today.isoformat()},LOT-Y202,{(today + datetime.timedelta(days=12)).isoformat()}
SKU-EGG-03,15,{today.isoformat()},LOT-E303,{(today + datetime.timedelta(days=18)).isoformat()}
SKU-BRD-08,5,{today.isoformat()},LOT-B404,{(today + datetime.timedelta(days=3)).isoformat()}
SKU-TOW-27,0,{today.isoformat()},LOT-T505,
"""
    (SAMPLE_DIR / "stock.csv").write_text(stock_csv_content, encoding="utf-8")

    # Sample Market Signals CSV
    market_csv_content = f"""date,scope_type,scope_value,signal_type,value,notes
{today.isoformat()},category,Dairy & Fresh,festival_flag,1.25,Diwali week surge in milk and butter (+25%)
{today.isoformat()},category,Beverages,seasonality_index,1.15,Warm weather cold beverage index
{today.isoformat()},sku,SKU-RIC-09,price_index,0.95,Wholesale commodity price discount (-5%)
"""
    (SAMPLE_DIR / "market.csv").write_text(market_csv_content, encoding="utf-8")

    db.commit()

    return {
        "status": "success",
        "products_count": len(products_data),
        "sales_records_count": total_sales,
        "sample_files_created": ["gst_invoices.csv", "stock.csv", "market.csv"],
        "message": f"Successfully initialized StockSense v2 with {len(products_data)} products, {total_sales} transactions, GST lines, stock batches, market signals, purchase orders, and automated alerts."
    }
