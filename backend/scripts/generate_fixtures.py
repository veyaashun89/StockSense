import os
import csv
import io
import zxingcpp
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "barcodes")
os.makedirs(fixtures_dir, exist_ok=True)

labels_path = os.path.join(fixtures_dir, "labels.csv")

def create_raw_code_img(text: str, fmt: zxingcpp.BarcodeFormat, scale: int = 2) -> Image.Image:
    bc = zxingcpp.create_barcode(text, fmt)
    arr = np.array(zxingcpp.write_barcode_to_image(bc))
    img = Image.fromarray(arr).convert("RGB")
    w, h = img.size
    return img.resize((w * scale, h * scale), resample=Image.BILINEAR)

fixtures = [
    # 1-6 Printed Packs (Clean)
    {"file": "pack_amul_milk_ean13.png", "text": "8901262010054", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "printed_pack", "expected": "8901262010054", "should_decode": True, "reason": None},
    {"file": "pack_bread_ean13.png", "text": "8901063012011", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "printed_pack", "expected": "8901063012011", "should_decode": True, "reason": None},
    {"file": "pack_maggi_ean13.png", "text": "8901058852462", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "printed_pack", "expected": "8901058852462", "should_decode": True, "reason": None},
    {"file": "pack_rice_ean13.png", "text": "8906007280129", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "printed_pack", "expected": "8906007280129", "should_decode": True, "reason": None},
    {"file": "pack_oil_ean13.png", "text": "8906007281010", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "printed_pack", "expected": "8906007281010", "should_decode": True, "reason": None},
    {"file": "pack_soap_ean13.png", "text": "8901396381006", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "printed_pack", "expected": "8901396381006", "should_decode": True, "reason": None},

    # 7-11 On a Screen (LCD screen presentation)
    {"file": "screen_qr_store_url.png", "text": "https://stocksense.ai/pos", "fmt": zxingcpp.BarcodeFormat.QRCode, "type": "screen", "expected": "https://stocksense.ai/pos", "should_decode": True, "reason": None},
    {"file": "screen_ean13_colgate.png", "text": "8901314010520", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "screen", "expected": "8901314010520", "should_decode": True, "reason": None},
    {"file": "screen_upca_beverage.png", "text": "012345678905", "fmt": zxingcpp.BarcodeFormat.UPCA, "type": "screen", "expected": "012345678905", "should_decode": True, "reason": None},
    {"file": "screen_code128_batch.png", "text": "BATCH-2026-OCT", "fmt": zxingcpp.BarcodeFormat.Code128, "type": "screen", "expected": "BATCH-2026-OCT", "should_decode": True, "reason": None},
    {"file": "screen_ean8_candy.png", "text": "96385074", "fmt": zxingcpp.BarcodeFormat.EAN8, "type": "screen", "expected": "96385074", "should_decode": True, "reason": None},

    # 12-15 At an Angle
    {"file": "angle_15deg_maggi.png", "text": "8901058852462", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "angle_15", "expected": "8901058852462", "should_decode": True, "reason": None},
    {"file": "angle_30deg_bread.png", "text": "8901063012011", "fmt": zxingcpp.BarcodeFormat.QRCode, "type": "angle_30", "expected": "8901063012011", "should_decode": True, "reason": None},
    {"file": "angle_45deg_qr.png", "text": "POS-TERMINAL-01", "fmt": zxingcpp.BarcodeFormat.QRCode, "type": "angle_45", "expected": "POS-TERMINAL-01", "should_decode": True, "reason": None},
    {"file": "angle_rotated_90deg_milk.png", "text": "8901262010054", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "angle_90", "expected": "8901262010054", "should_decode": True, "reason": None},

    # 16-20 In Dim Light & Shadow
    {"file": "dim_light_amul_milk.png", "text": "8901262010054", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "dim_light", "expected": "8901262010054", "should_decode": True, "reason": None},
    {"file": "dim_light_soap_ean13.png", "text": "8901396381006", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "dim_light", "expected": "8901396381006", "should_decode": True, "reason": None},
    {"file": "dim_light_qr_order.png", "text": "ORDER-IND-9941", "fmt": zxingcpp.BarcodeFormat.QRCode, "type": "dim_light", "expected": "ORDER-IND-9941", "should_decode": True, "reason": None},
    {"file": "shadow_across_rice.png", "text": "8906007280129", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "shadow", "expected": "8906007280129", "should_decode": True, "reason": None},
    {"file": "mild_perspective_oil.png", "text": "8906007281010", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "perspective", "expected": "8906007281010", "should_decode": True, "reason": None},

    # 21-24 Failure Cases
    {"file": "failure_heavy_blur.png", "text": "8901058852462", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "blur", "expected": "", "should_decode": False, "reason": "blur"},
    {"file": "failure_specular_glare.png", "text": "8901262010054", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "glare", "expected": "", "should_decode": False, "reason": "glare"},
    {"file": "failure_tiny_distance.png", "text": "8901396381006", "fmt": zxingcpp.BarcodeFormat.EAN13, "type": "too_small", "expected": "", "should_decode": False, "reason": "too small"},
    {"file": "failure_no_code_apple.png", "text": "", "fmt": None, "type": "no_code", "expected": "", "should_decode": False, "reason": "no code visible"}
]

for item in fixtures:
    img = Image.new("RGB", (640, 480), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    if item["type"] == "no_code":
        draw.ellipse([220, 140, 420, 340], fill=(210, 30, 30), outline=(150, 20, 20), width=3)
        draw.rectangle([315, 110, 325, 140], fill=(90, 50, 20))
        draw.text((230, 360), "Fresh Organic Apple", fill=(60, 60, 60))
    elif item["type"] == "printed_pack":
        draw.rectangle([50, 50, 590, 430], fill=(255, 255, 255), outline=(180, 180, 180), width=2)
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        cw, ch = code_img.size
        img.paste(code_img, ((640 - cw) // 2, 170))
        draw.text((150, 340), f"Product Code: {item['text']}", fill=(0, 0, 0))
    elif item["type"] == "screen":
        draw.rectangle([40, 40, 600, 440], fill=(25, 30, 35), outline=(60, 70, 80), width=4)
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        cw, ch = code_img.size
        # White quiet zone
        draw.rectangle([(640 - cw) // 2 - 20, 140 - 20, (640 - cw) // 2 + cw + 20, 140 + ch + 20], fill=(255, 255, 255))
        img.paste(code_img, ((640 - cw) // 2, 140))
    elif item["type"] == "angle_15":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        rot = code_img.rotate(15, resample=Image.BICUBIC, expand=True, fillcolor=(240, 240, 240))
        cw, ch = rot.size
        img.paste(rot, ((640 - cw) // 2, (480 - ch) // 2))
    elif item["type"] == "angle_30":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=3)
        rot = code_img.rotate(30, resample=Image.BICUBIC, expand=True, fillcolor=(240, 240, 240))
        cw, ch = rot.size
        img.paste(rot, ((640 - cw) // 2, (480 - ch) // 2))
    elif item["type"] == "angle_45":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=3)
        rot = code_img.rotate(45, resample=Image.BICUBIC, expand=True, fillcolor=(240, 240, 240))
        cw, ch = rot.size
        img.paste(rot, ((640 - cw) // 2, (480 - ch) // 2))
    elif item["type"] == "angle_90":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        rot = code_img.rotate(90, resample=Image.BICUBIC, expand=True, fillcolor=(240, 240, 240))
        cw, ch = rot.size
        img.paste(rot, ((640 - cw) // 2, (480 - ch) // 2))
    elif item["type"] == "dim_light":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        cw, ch = code_img.size
        img.paste(code_img, ((640 - cw) // 2, 150))
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.40)
    elif item["type"] == "shadow":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        cw, ch = code_img.size
        img.paste(code_img, ((640 - cw) // 2, 150))
        shadow = Image.new("RGBA", (640, 480), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow)
        sdraw.polygon([(0, 220), (640, 320), (640, 480), (0, 480)], fill=(0, 0, 0, 160))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    elif item["type"] == "perspective":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        cw, ch = code_img.size
        img.paste(code_img, ((640 - cw) // 2, 150))
    elif item["type"] == "blur":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        code_img = code_img.filter(ImageFilter.GaussianBlur(radius=20))
        cw, ch = code_img.size
        img.paste(code_img, ((640 - cw) // 2, 150))
    elif item["type"] == "glare":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=2)
        cw, ch = code_img.size
        img.paste(code_img, ((640 - cw) // 2, 150))
        draw = ImageDraw.Draw(img)
        # Specular flash washing out 90% of bars
        draw.rectangle([100, 140, 540, 340], fill=(255, 255, 255))
    elif item["type"] == "too_small":
        code_img = create_raw_code_img(item["text"], item["fmt"], scale=1)
        tiny = code_img.resize((14, 6))
        img.paste(tiny, (313, 237))

    img_path = os.path.join(fixtures_dir, item["file"])
    img.save(img_path)

# Write labels.csv
with open(labels_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "expected_value", "type", "should_decode", "failure_reason"])
    for it in fixtures:
        writer.writerow([it["file"], it["expected"], it["type"], it["should_decode"], it["reason"] or ""])

print(f"Generated {len(fixtures)} barcode fixtures in {fixtures_dir}")
print(f"Labels written to {labels_path}")
