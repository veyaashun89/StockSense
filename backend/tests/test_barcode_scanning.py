import pytest
import numpy as np
from PIL import Image
import zxingcpp
from backend.services.vision_service import decode_barcodes_from_image, recognize_product_cv
from backend.database import init_db

def test_decode_six_distinct_barcode_formats():
    """
    Phase 1 Requirement:
    Test decoder with at least 6 printed or on-screen codes of different formats.
    Measures and asserts 100% decode success rate.
    """
    test_suite = [
        {"format": zxingcpp.BarcodeFormat.QRCode, "text": "STOCKSENSE-MLK-001", "name": "QR Code"},
        {"format": zxingcpp.BarcodeFormat.EAN13, "text": "8901030383458", "name": "EAN-13"},
        {"format": zxingcpp.BarcodeFormat.Code128, "text": "SKU-BREAD-WHT", "name": "Code 128"},
        {"format": zxingcpp.BarcodeFormat.UPCA, "text": "012345678905", "name": "UPC-A"},
        {"format": zxingcpp.BarcodeFormat.DataMatrix, "text": "SKU-MAGGI-70", "name": "Data Matrix"},
        {"format": zxingcpp.BarcodeFormat.Code39, "text": "SKU-RICE-1KG", "name": "Code 39"}
    ]

    successful_decodes = 0
    total_tests = len(test_suite)

    for item in test_suite:
        # Generate barcode image
        barcode = zxingcpp.create_barcode(item["text"], item["format"])
        arr = np.array(zxingcpp.write_barcode_to_image(barcode))
        img = Image.fromarray(arr)

        # Decode using vision_service
        decoded_list = decode_barcodes_from_image(img)
        assert len(decoded_list) >= 1, f"Failed to decode {item['name']}"
        decoded = decoded_list[0]

        # Verify decoded content and geometry
        # Note: UPCA in zxing may format as '0012345678905' or '012345678905'
        assert item["text"] in decoded["value"] or decoded["value"] in item["text"]
        assert len(decoded["bounding_box"]) == 4
        assert len(decoded["pixel_box"]) == 4
        assert decoded["is_valid"] is True
        successful_decodes += 1

    success_rate = (successful_decodes / total_tests) * 100.0
    print(f"\n[PHASE 1 AUDIT] Tested {total_tests} barcode formats. Decode success rate: {success_rate:.1f}%")
    assert success_rate == 100.0

def test_decode_multiple_barcodes_in_single_frame():
    """
    Phase 1 Requirement:
    Decode multiple codes per frame. Return value, format, and bounding box.
    """
    bc1 = zxingcpp.create_barcode("MLK-001", zxingcpp.BarcodeFormat.QRCode)
    bc2 = zxingcpp.create_barcode("BRD-002", zxingcpp.BarcodeFormat.Code128)

    arr1 = np.array(zxingcpp.write_barcode_to_image(bc1))
    arr2 = np.array(zxingcpp.write_barcode_to_image(bc2))

    img1 = Image.fromarray(arr1)
    img2 = Image.fromarray(arr2)

    # Place both barcodes side by side on a single canvas
    combined = Image.new("L", (600, 250), color=255)
    combined.paste(img1.resize((150, 150)), (30, 50))
    combined.paste(img2.resize((260, 100)), (240, 75))

    results = decode_barcodes_from_image(combined)
    assert len(results) == 2, f"Expected 2 barcodes, found {len(results)}"

    values = [r["value"] for r in results]
    formats = [r["format"] for r in results]

    assert "MLK-001" in values
    assert "BRD-002" in values
    assert "QRCode" in formats
    assert "Code128" in formats

    for r in results:
        ymin, xmin, ymax, xmax = r["bounding_box"]
        assert 0.0 <= ymin < ymax <= 1.0
        assert 0.0 <= xmin < xmax <= 1.0

def test_recognize_product_cv_barcode_scan_flow():
    """
    Tests automated barcode extraction inside recognize_product_cv.
    """
    from backend.app import create_app
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        bc = zxingcpp.create_barcode("SKU-MLK-01", zxingcpp.BarcodeFormat.QRCode)
        arr = np.array(zxingcpp.write_barcode_to_image(bc))
        img = Image.fromarray(arr)

        # Call recognition passing the generated barcode image
        res = recognize_product_cv(image_input=img)
        assert res.get("matched") is True
        assert res.get("recognition_mode") == "barcode_scan"
        assert res.get("confidence") == 1.0
        assert res["product"]["sku"] == "SKU-MLK-01"


