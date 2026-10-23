import datetime
from flask import Blueprint, request, jsonify
from backend.services.vision_service import recognize_product_cv
from backend.services.payment_service import create_payment_request, verify_and_settle_payment
from backend.services.alert_service import evaluate_and_generate_alerts
from backend.services.auth_service import require_roles
from backend.database import get_db

scanner_bp = Blueprint("scanner", __name__)

@scanner_bp.route("/scanner/recognize", methods=["POST"])
def recognize_product():
    """
    Computer Vision Product Recognition Endpoint.
    Accepts webcam canvas frame (base64), uploaded image, or scanned barcode/QR.
    """
    data = request.get_json() or {}
    image_data = data.get("image_data")
    barcode_text = data.get("barcode")
    detected_label = data.get("label")

    # If multipart file uploaded
    if not image_data and "file" in request.files:
        import base64
        file_bytes = request.files["file"].read()
        image_data = base64.b64encode(file_bytes).decode("utf-8")

    result = recognize_product_cv(
        image_input=image_data,
        barcode_text=barcode_text,
        detected_label=detected_label
    )
    return jsonify(result), 200

@scanner_bp.route("/scanner/quick-sale", methods=["POST"])
@require_roles("retailer", "admin")
def quick_sale():
    """
    Instantly record a single-item sale from the scanner terminal.
    Decrements current stock, writes to sales ledger and inventory_movements.
    """
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    if not product_id or quantity <= 0:
        return jsonify({"error": "Valid product_id and positive quantity are required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, sku, name, current_stock, selling_price FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        return jsonify({"error": "Product not found"}), 404

    current_stock = prod["current_stock"]
    new_stock = max(0, current_stock - quantity)
    today_str = datetime.date.today().isoformat()

    # Deduct stock
    cursor.execute("UPDATE products SET current_stock = ? WHERE id = ?", (new_stock, product_id))

    # Log in sales ledger
    cursor.execute("""
        INSERT INTO sales (product_id, sku, sale_date, quantity_sold, source)
        VALUES (?, ?, ?, ?, 'scanner_quick_sale')
    """, (product_id, prod["sku"], today_str, quantity))

    # Log in inventory movements audit
    cursor.execute("""
        INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reason)
        VALUES (?, 'SALE', ?, ?, 'POS Camera Scanner quick-sale')
    """, (product_id, -quantity, new_stock))

    db.commit()

    # Sync alerts in background
    try:
        evaluate_and_generate_alerts()
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "product_id": product_id,
        "sku": prod["sku"],
        "name": prod["name"],
        "sold_quantity": quantity,
        "new_stock": new_stock,
        "total_value": round(quantity * prod["selling_price"], 2),
        "message": f"Sold {quantity} unit(s) of {prod['name']}. Stock updated from {current_stock} to {new_stock}."
    }), 200

@scanner_bp.route("/scanner/quick-restock", methods=["POST"])
def quick_restock():
    """
    Instantly restock a product batch from the scanner terminal.
    """
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 10))
    batch_id = data.get("batch_id") or f"RESTOCK-{datetime.date.today().strftime('%m%d')}"
    expiry_date = data.get("expiry_date")

    if not product_id or quantity <= 0:
        return jsonify({"error": "Valid product_id and positive quantity required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, sku, name, current_stock FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        return jsonify({"error": "Product not found"}), 404

    new_stock = prod["current_stock"] + quantity
    cursor.execute("UPDATE products SET current_stock = ? WHERE id = ?", (new_stock, product_id))

    # Record movement
    cursor.execute("""
        INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reason)
        VALUES (?, 'RESTOCK', ?, ?, ?)
    """, (product_id, quantity, new_stock, f"Scanner restock batch {batch_id}"))

    # Record stock batch if expiry given
    if expiry_date:
        cursor.execute("""
            INSERT INTO stock_batches (product_id, sku, batch_id, quantity, expiry_date)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, prod["sku"], batch_id, quantity, expiry_date))

    db.commit()

    return jsonify({
        "status": "success",
        "product_id": product_id,
        "sku": prod["sku"],
        "name": prod["name"],
        "added_quantity": quantity,
        "new_stock": new_stock,
        "message": f"Restocked {quantity} units of {prod['name']}."
    }), 200

@scanner_bp.route("/payment/generate-qr", methods=["POST"])
def generate_payment_qr():
    """
    Generate dynamic UPI QR Code for retail POS cart or purchase order payment.
    """
    data = request.get_json() or {}
    amount = float(data.get("amount", 0))
    purpose = data.get("purpose", "retail_pos")
    ref_id = data.get("reference_id")

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than 0"}), 400

    qr_payload = create_payment_request(
        amount=amount,
        purpose=purpose,
        reference_id=ref_id
    )
    return jsonify(qr_payload), 200

@scanner_bp.route("/payment/verify", methods=["POST"])
def verify_payment():
    """
    Verify payment settlement via UPI reference or scanned UTR receipt.
    Reconciles inventory movements for items in cart.
    """
    data = request.get_json() or {}
    txn_ref = data.get("transaction_ref") or f"TXN-{datetime.date.today().strftime('%Y%m%d')}"
    amount = float(data.get("amount", 0))
    method = data.get("payment_method", "UPI_QR")
    utr = data.get("utr_number")
    cart_items = data.get("cart_items", [])
    po_id = data.get("purchase_order_id")

    receipt = verify_and_settle_payment(
        transaction_ref=txn_ref,
        amount=amount,
        payment_method=method,
        utr_number=utr,
        cart_items=cart_items
    )

    # If linked to a purchase order payment, record note in PO
    if po_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE purchase_orders 
            SET notes = COALESCE(notes, '') || ' [PAID via UPI ' || ? || ']'
            WHERE id = ?
        """, (receipt["utr_number"], po_id))
        db.commit()
        receipt["purchase_order_id"] = po_id

    # Sync alerts
    try:
        evaluate_and_generate_alerts()
    except Exception:
        pass

    return jsonify(receipt), 200
