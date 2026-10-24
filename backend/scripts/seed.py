import sys
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database import init_db, get_db_session, hash_password
from backend.models.orm_models import (
    User, Shop, Supplier, Product, Inventory, InventoryMovement, 
    Sale, SaleItem, Alert, Setting
)
from backend.utils.money import rupees_to_paise

def load_master_products():
    import csv
    master_path = Path(__file__).resolve().parent.parent / "data" / "products_master.csv"
    products = []
    if master_path.exists():
        with open(master_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                products.append({
                    "sku": r["sku"].strip(),
                    "name": r["name"].strip(),
                    "category": r["category"].strip(),
                    "retail_price": float(r.get("retail_price_paise", 0)) / 100.0 if r.get("retail_price_paise") else float(r.get("selling_price", 0)),
                    "unit_cost": float(r.get("unit_cost_paise", 0)) / 100.0 if r.get("unit_cost_paise") else float(r.get("unit_cost", 0)),
                    "is_perishable": int(r.get("is_perishable") or 0),
                    "shelf_life_days": int(r["shelf_life_days"]) if r.get("shelf_life_days") and r["shelf_life_days"].strip() else None,
                    "lead_time_days": int(r.get("lead_time_days") or 2),
                    "min_order_qty": int(r.get("min_order_qty") or 10),
                    "pack_size": int(r.get("pack_size") or 1),
                    "safety_buffer_days": int(r.get("safety_buffer_days") or 2),
                    "stock": int(r.get("current_stock") or 20),
                    "barcode": r.get("barcode", "").strip() or None
                })
    return products

DEMO_PRODUCTS = load_master_products()

def seed_database():
    """Idempotent seed script creating/updating demo users, products, starting inventory, and sample sales."""
    print("[Seed] Initializing SQLite schema and default tables...")
    init_db(drop_all=False)

    with get_db_session() as session:
        # 1. Ensure Default Shop
        shop = session.query(Shop).filter_by(id=1).first()
        if not shop:
            shop = Shop(id=1, name="Lakshmi Supermarket (Store #1)", address="104 MG Road, Indiranagar, Bengaluru")
            session.add(shop)
            session.flush()

        # 2. Ensure Default Supplier
        supplier = session.query(Supplier).filter_by(name="FreshValley Wholesale Supply").first()
        if not supplier:
            supplier = Supplier(
                name="FreshValley Wholesale Supply",
                lead_time=3,
                min_order_qty=10,
                pack_size=5,
                contact_email="supply@freshvalley.in"
            )
            session.add(supplier)
            session.flush()

        # 3. Ensure 3 Deterministic Demo Users
        users_data = [
            ("retailer@stocksense.in", "retailer123", "retailer", "Ravi Sharma (Store Owner)"),
            ("wholesaler@stocksense.in", "wholesaler123", "wholesaler", "Apex Distribution Network"),
            ("dealer@stocksense.in", "dealer123", "dealer", "Metro Regional Dealers Hub"),
            ("admin@stocksense.in", "admin123", "admin", "StockSense Platform Operations"),
            # Alternate convenience alias
            ("retailer@stocksense.ai", "retailer123", "retailer", "Ravi Sharma (Store Owner)"),
            ("wholesaler@stocksense.ai", "wholesaler123", "wholesaler", "Apex Distribution Network"),
            ("dealer@stocksense.ai", "dealer123", "dealer", "Metro Regional Dealers Hub"),
            ("admin@stocksense.ai", "admin123", "admin", "StockSense Platform Operations"),
        ]

        user_map = {}
        for email, pwd, role, name in users_data:
            user = session.query(User).filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    password_hash=hash_password(pwd),
                    role=role,
                    name=name,
                    shop_id=shop.id,
                    active=1
                )
                session.add(user)
                session.flush()
            user_map[role] = user

        retailer_user = user_map.get("retailer")
        owner_id = retailer_user.id if retailer_user else 1

        # 4. Upsert 6 Demo Products & Starting Inventory
        print(f"[Seed] Upserting {len(DEMO_PRODUCTS)} demo products & starting inventory...")
        for pdata in DEMO_PRODUCTS:
            sku = pdata["sku"]
            prod = session.query(Product).filter_by(sku=sku).first()
            if not prod:
                prod = Product(
                    shop_id=shop.id,
                    sku=sku,
                    name=pdata["name"],
                    category=pdata["category"],
                    unit="unit",
                    retail_price_paise=rupees_to_paise(pdata["retail_price"]),
                    unit_cost_paise=rupees_to_paise(pdata["unit_cost"]),
                    gst_rate=5.0 if pdata["is_perishable"] else 18.0,
                    current_stock=pdata["stock"],
                    supplier_id=supplier.id,
                    lead_time_days=pdata["lead_time_days"],
                    is_perishable=pdata["is_perishable"],
                    shelf_life_days=pdata["shelf_life_days"],
                    min_order_qty=pdata["min_order_qty"],
                    pack_size=pdata["pack_size"],
                    safety_buffer_days=pdata["safety_buffer_days"],
                    barcode=pdata["barcode"],
                    is_active=1
                )
                session.add(prod)
                session.flush()
            else:
                prod.name = pdata["name"]
                prod.category = pdata["category"]
                prod.retail_price_paise = rupees_to_paise(pdata["retail_price"])
                prod.unit_cost_paise = rupees_to_paise(pdata["unit_cost"])
                prod.barcode = pdata["barcode"]
                if (prod.current_stock or 0) < pdata["stock"]:
                    prod.current_stock = pdata["stock"]
                session.flush()

            # Upsert Inventory
            inv = session.query(Inventory).filter_by(product_id=prod.id, owner_id=owner_id).first()
            if not inv:
                inv = Inventory(
                    product_id=prod.id,
                    owner_id=owner_id,
                    on_hand=pdata["stock"],
                    reorder_level=pdata["min_order_qty"]
                )
                session.add(inv)
                session.flush()
            else:
                if (inv.on_hand or 0) < pdata["stock"]:
                    inv.on_hand = pdata["stock"]
                    session.flush()

                # Log initial movement
                init_movement = InventoryMovement(
                    product_id=prod.id,
                    owner_id=owner_id,
                    delta=pdata["stock"],
                    balance_after=pdata["stock"],
                    reason="INITIAL",
                    reference="Initial Seed Balance"
                )
                session.add(init_movement)
                session.flush()

        # 5. Seed Sample Sales if no sales exist
        sale_count = session.query(Sale).count()
        if sale_count == 0:
            print("[Seed] Seeding sample completed sale transaction...")
            milk_prod = session.query(Product).filter_by(sku="SKU-MLK-01").first()
            if milk_prod:
                subtotal_paise = rupees_to_paise(54.0 * 2)
                tax_paise = rupees_to_paise(5.40)
                total_paise = subtotal_paise + tax_paise
                sample_sale = Sale(
                    owner_id=owner_id,
                    shop_id=shop.id,
                    product_id=milk_prod.id,
                    sku=milk_prod.sku,
                    quantity_sold=2,
                    utr="UTR-DEMO-00101",
                    subtotal_paise=subtotal_paise,
                    tax_paise=tax_paise,
                    total_paise=total_paise,
                    payment_status="PAID",
                    source="pos_scanner",
                    sale_date=datetime.date.today().isoformat()
                )
                session.add(sample_sale)
                session.flush()

                item = SaleItem(
                    sale_id=sample_sale.id,
                    product_id=milk_prod.id,
                    qty=2,
                    unit_price_paise=milk_prod.retail_price_paise,
                    line_total_paise=subtotal_paise
                )
                session.add(item)
                session.flush()

        print("[Seed] Seeding completed successfully. Ready for operation.")

if __name__ == "__main__":
    seed_database()
