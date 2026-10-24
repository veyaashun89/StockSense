import datetime
import time
import threading
import base64
import io
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify
from backend.services.vision_service import recognize_product_cv, decode_codes
from backend.services.payment_service import create_payment_request, verify_and_settle_payment
from backend.services.alert_service import evaluate_and_generate_alerts
from backend.services.auth_service import require_roles
from backend.database import get_db
from backend.services.notification_rules import evaluate_scanner_failure
from backend.workers.notification_worker import enqueue_notification

scanner_bp = Blueprint("scanner", __name__)

_scanner_failure_timestamps: List[float] = []
_scanner_lock = threading.Lock()

MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
_decode_rate_limits: Dict[str, List[float]] = {}
_decode_rate_lock = threading.Lock()
MAX_DECODES_PER_SEC = 15

def _check_decode_rate_limit(client_id: str) -> bool:
    now = time.time()
    with _decode_rate_lock:
        timestamps = _decode_rate_limits.setdefault(client_id, [])
        valid = [t for t in timestamps if now - t < 1.0]
        if len(valid) >= MAX_DECODES_PER_SEC:
            _decode_rate_limits[client_id] = valid
            return False
        valid.append(now)
        _decode_rate_limits[client_id] = valid
        return True

def reset_scanner_failures():
    with _scanner_lock:
        _scanner_failure_timestamps.clear()

def record_scanner_failure(reason: str = "Hardware timeout", terminal_id: str = "Register-1") -> int:
    """
    Records a scanner recognition failure in a 10-minute sliding window.
    Triggers 'scanner_failure' notification when 3 or more failures occur in 10 minutes.
    """
    now = time.time()
    cutoff = now - 600.0  # 10 minutes
    with _scanner_lock:
        _scanner_failure_timestamps.append(now)
        recent = [t for t in _scanner_failure_timestamps if t >= cutoff]
        _scanner_failure_timestamps[:] = recent
        count = len(recent)

    if count >= 3:
        try:
            eval_res = evaluate_scanner_failure(
                failure_count_in_10m=count,
                reason=reason,
                terminal_id=terminal_id
            )
            if eval_res:
                enqueue_notification(
                    rule=eval_res["rule"],
                    title=eval_res["title"],
                    message=eval_res["message"],
                    priority=eval_res["priority"],
                    event_ref=f"scan_fail_{terminal_id}_{int(now)}",
                    tags=eval_res["tags"],
                    dedup_key=eval_res["dedup_key"],
                    owner_id=1
                )
        except Exception:
            pass

    return count


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

    if not result.get("matched") and (barcode_text or image_data):
        record_scanner_failure(reason="Recognition failure or timeout")

    return jsonify(result), 200

@scanner_bp.route("/scanner/decode", methods=["POST"])
def decode_scanner_frame():
    """
    Optical Barcode and QR Code Decoding Endpoint.
    Accepts base64 JPEG or PNG (max 2 MB) or multipart image upload.
    Validates size and type, enforces rate limits, decodes codes via zxing-cpp,
    and looks up each decoded code in products.barcode (and products.sku).
    Returns:
      {
        "status": "matched" | "unknown_code" | "no_code",
        "product": ProductDict | None,
        "codes": List[DecodedCode]
      }
    Never returns a stack trace.
    """
    client_ip = request.remote_addr or "127.0.0.1"
    if not _check_decode_rate_limit(client_ip):
        return jsonify({
            "status": "rate_limited",
            "error": "Rate limit exceeded. Maximum 15 requests per second.",
            "product": None,
            "codes": []
        }), 429

    raw_bytes = None
    try:
        data = request.get_json(silent=True) or {}
        image_input = data.get("image") or data.get("image_data") or data.get("frame")

        if image_input:
            if isinstance(image_input, str):
                clean_str = image_input
                if "base64," in clean_str:
                    clean_str = clean_str.split("base64,")[1]
                raw_bytes = base64.b64decode(clean_str)
            elif isinstance(image_input, bytes):
                raw_bytes = image_input
        elif "file" in request.files:
            raw_bytes = request.files["file"].read()
        elif request.data:
            raw_bytes = request.data
    except Exception:
        return jsonify({
            "status": "no_code",
            "error": "Invalid base64 image encoding.",
            "product": None,
            "codes": []
        }), 400

    if not raw_bytes:
        return jsonify({
            "status": "no_code",
            "error": "No image data provided. Send base64 JPEG or PNG in request body.",
            "product": None,
            "codes": []
        }), 400

    if len(raw_bytes) > MAX_IMAGE_SIZE_BYTES:
        return jsonify({
            "status": "no_code",
            "error": f"Image exceeds 2 MB limit (received {len(raw_bytes)} bytes).",
            "product": None,
            "codes": []
        }), 400

    try:
        from PIL import Image
        pil_img = Image.open(io.BytesIO(raw_bytes))
        img_format = (pil_img.format or "").upper()
        if img_format not in ("JPEG", "PNG", "JPG"):
            return jsonify({
                "status": "no_code",
                "error": f"Unsupported image format '{img_format}'. Only JPEG and PNG are allowed.",
                "product": None,
                "codes": []
            }), 400
    except Exception:
        return jsonify({
            "status": "no_code",
            "error": "Invalid or corrupt image format. Only JPEG and PNG are allowed.",
            "product": None,
            "codes": []
        }), 400

    try:
        decoded_codes = decode_codes(raw_bytes)
    except Exception:
        return jsonify({
            "status": "no_code",
            "error": "Optical decoding process encountered an error.",
            "product": None,
            "codes": []
        }), 200

    if not decoded_codes:
        return jsonify({
            "status": "no_code",
            "product": None,
            "codes": []
        }), 200

    try:
        db = get_db()
        cursor = db.cursor()
        for code in decoded_codes:
            val = code["value"].strip()
            if not val:
                continue

            cursor.execute("""
                SELECT p.*, s.name as supplier_name,
                       COALESCE(i.on_hand, p.current_stock) as on_hand_stock
                FROM products p
                LEFT JOIN suppliers s ON p.supplier_id = s.id
                LEFT JOIN inventory i ON p.id = i.product_id
                WHERE (p.barcode = ? OR p.sku = ?) AND p.is_active = 1
                LIMIT 1
            """, (val, val))
            prod_row = cursor.fetchone()
            if prod_row:
                prod = dict(prod_row)
                if "retail_price_paise" not in prod or not prod["retail_price_paise"]:
                    prod["retail_price_paise"] = int(round((prod.get("selling_price") or 0.0) * 100))
                if "unit_cost_paise" not in prod or not prod["unit_cost_paise"]:
                    prod["unit_cost_paise"] = int(round((prod.get("unit_cost") or 0.0) * 100))
                prod["selling_price"] = float(prod["retail_price_paise"] / 100.0)
                prod["current_stock"] = int(prod.get("on_hand_stock", prod.get("current_stock", 0)))

                return jsonify({
                    "status": "matched",
                    "product": prod,
                    "codes": decoded_codes,
                    "matched_code": val
                }), 200

        return jsonify({
            "status": "unknown_code",
            "product": None,
            "codes": decoded_codes,
            "primary_code": decoded_codes[0]["value"]
        }), 200

    except Exception:
        return jsonify({
            "status": "unknown_code",
            "product": None,
            "codes": decoded_codes
        }), 200


@scanner_bp.route("/scanner/report-failure", methods=["POST"])
def report_scanner_failure():
    """
    Allow client POS terminal to report camera feed drop or timeout.
    Triggers notification on 3rd failure in 10 minutes.
    """
    data = request.get_json() or {}
    reason = data.get("reason", "Webcam stream disconnected")
    terminal = data.get("terminal_id", "Register-1")
    count = record_scanner_failure(reason=reason, terminal_id=terminal)
    return jsonify({"status": "recorded", "failure_count_in_10m": count}), 200

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
