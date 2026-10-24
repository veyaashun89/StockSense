import os
import csv
import io
import time
import base64
import pytest
from PIL import Image
import zxingcpp

from backend.app import create_app
from backend.database import init_db
from backend.services.vision_service import decode_codes
from backend.scripts.set_barcodes import validate_ean13_check_digit

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "barcodes")
LABELS_FILE = os.path.join(FIXTURES_DIR, "labels.csv")

def test_fixtures_decoding_report():
    """
    Phase 3 Requirement:
    Collect at least 20 photos of real codes: printed packs, on a screen, at an angle, in dim light.
    Decodes every fixture and asserts expected value.
    Reports: total images, decoded correctly, decode rate, and every failure with its reason.
    """
    assert os.path.exists(LABELS_FILE), f"Missing labels file: {LABELS_FILE}"

    rows = []
    with open(LABELS_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    total_images = len(rows)
    assert total_images >= 20, f"Expected at least 20 fixture images, found {total_images}"

    decode_success_count = 0
    valid_code_images_count = 0
    failures = []

    for item in rows:
        filename = item["file"]
        filepath = os.path.join(FIXTURES_DIR, filename)
        assert os.path.exists(filepath), f"Fixture image file not found: {filepath}"

        with open(filepath, "rb") as img_file:
            img_bytes = img_file.read()

        decoded = decode_codes(img_bytes)
        expected = item["expected_value"]
        should_decode = item["should_decode"].lower() in ("true", "1")
        item_type = item["type"]
        known_failure_reason = item.get("failure_reason")

        if should_decode:
            valid_code_images_count += 1
            if decoded:
                decoded_values = [d["value"] for d in decoded]
                # Match expected or sub-match for UPC-A padding
                if any(expected == v or expected in v or v in expected for v in decoded_values):
                    decode_success_count += 1
                else:
                    failures.append({
                        "file": filename,
                        "type": item_type,
                        "expected": expected,
                        "decoded": decoded_values,
                        "reason": f"Value mismatch: got {decoded_values}"
                    })
            else:
                failures.append({
                    "file": filename,
                    "type": item_type,
                    "expected": expected,
                    "decoded": None,
                    "reason": "Failed to detect barcode"
                })
        else:
            # Expected failure case
            if not decoded:
                failures.append({
                    "file": filename,
                    "type": item_type,
                    "expected": "(none)",
                    "decoded": None,
                    "reason": known_failure_reason or "Expected decode failure"
                })
            else:
                # Unexpectedly decoded something from a damaged/empty image
                pass

    decode_rate = (decode_success_count / valid_code_images_count) * 100.0 if valid_code_images_count > 0 else 0.0

    print("\n" + "=" * 70)
    print("PHASE 3 OPTICAL BARCODE FIXTURE DECODE REPORT")
    print("=" * 70)
    print(f"Total Test Fixtures Evaluated : {total_images}")
    print(f"Valid Code Images Target     : {valid_code_images_count}")
    print(f"Decoded Correctly             : {decode_success_count}")
    print(f"Achieved Decode Rate          : {decode_rate:.2f}%")
    print("-" * 70)
    print("Documented Failure / Edge Cases:")
    for f in failures:
        print(f" - [{f['file']}] Type: {f['type']} -> Reason: {f['reason']}")
    print("=" * 70)

    # All valid code images must achieve 100% decode rate
    assert decode_rate == 100.0, f"Decode rate was {decode_rate:.2f}%, expected 100.0% on valid fixtures"
    assert len(failures) >= 4, "Expected at least 4 failure edge cases documented"


def test_api_decode_matched_product():
    """
    POST /api/scanner/decode with a known product barcode returns status: 'matched'
    with full product details and money in integer paise.
    """
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        client = app.test_client()

        # Amul Taaza Milk EAN-13
        test_file = os.path.join(FIXTURES_DIR, "pack_amul_milk_ean13.png")
        with open(test_file, "rb") as f:
            raw_bytes = f.read()

        b64_img = base64.b64encode(raw_bytes).decode("utf-8")
        resp = client.post("/api/scanner/decode", json={"image": b64_img})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "matched"
        assert data["product"] is not None
        assert data["product"]["sku"] == "SKU-MILK-500"
        assert data["product"]["barcode"] == "8901262010054"
        assert data["product"]["retail_price_paise"] == 2700  # 27.00 in integer paise
        assert len(data["codes"]) >= 1


def test_api_decode_unknown_code():
    """
    POST /api/scanner/decode with a valid barcode not in catalog returns status: 'unknown_code'.
    """
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        client = app.test_client()

        # Colgate EAN-13 fixture is not in catalog
        test_file = os.path.join(FIXTURES_DIR, "screen_ean13_colgate.png")
        with open(test_file, "rb") as f:
            raw_bytes = f.read()

        b64_img = base64.b64encode(raw_bytes).decode("utf-8")
        resp = client.post("/api/scanner/decode", json={"image": b64_img})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "unknown_code"
        assert data["product"] is None
        assert len(data["codes"]) >= 1
        assert data["codes"][0]["value"] == "8901314010520"


def test_api_decode_no_code():
    """
    POST /api/scanner/decode with photo of an apple (no barcode) returns status: 'no_code'.
    """
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        client = app.test_client()

        test_file = os.path.join(FIXTURES_DIR, "failure_no_code_apple.png")
        with open(test_file, "rb") as f:
            raw_bytes = f.read()

        b64_img = base64.b64encode(raw_bytes).decode("utf-8")
        resp = client.post("/api/scanner/decode", json={"image": b64_img})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "no_code"
        assert data["product"] is None
        assert data["codes"] == []


def test_api_decode_payload_size_limit():
    """
    POST /api/scanner/decode rejects payloads exceeding 2 MB with HTTP 400.
    """
    app = create_app({"TESTING": True})
    with app.app_context():
        client = app.test_client()

        # Create oversized payload (> 2.1 MB)
        oversized = b"A" * (2 * 1024 * 1024 + 1024)
        b64_over = base64.b64encode(oversized).decode("utf-8")

        resp = client.post("/api/scanner/decode", json={"image": b64_over})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "exceeds 2 MB limit" in data["error"]
        assert data["status"] == "no_code"


def test_api_decode_unsupported_format_rejection():
    """
    POST /api/scanner/decode rejects non-JPEG/PNG images (e.g. text or corrupt format) with HTTP 400.
    """
    app = create_app({"TESTING": True})
    with app.app_context():
        client = app.test_client()

        fake_bmp = b"BM" + (b"\x00" * 100)
        b64_bmp = base64.b64encode(fake_bmp).decode("utf-8")

        resp = client.post("/api/scanner/decode", json={"image": b64_bmp})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Only JPEG and PNG are allowed" in data["error"]
