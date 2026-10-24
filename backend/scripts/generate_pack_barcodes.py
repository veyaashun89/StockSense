import os
import zxingcpp
import numpy as np
from PIL import Image, ImageDraw

out_dir = os.path.join(os.path.dirname(__file__), "..", "ml", "dataset", "barcodes")
os.makedirs(out_dir, exist_ok=True)

packs = [
    {
        "sku": "SKU-MILK-500",
        "name": "Amul Taaza Milk 500ml",
        "barcode": "8901262010054",
        "format": zxingcpp.BarcodeFormat.EAN13,
        "bg_color": (240, 245, 255),
        "accent_color": (30, 110, 210)
    },
    {
        "sku": "SKU-BREAD-WHT",
        "name": "Harvest Gold White Bread 400g",
        "barcode": "8901063012011",
        "format": zxingcpp.BarcodeFormat.EAN13,
        "bg_color": (250, 240, 220),
        "accent_color": (180, 80, 20)
    },
    {
        "sku": "SKU-MAGGI-70",
        "name": "Nestle Maggi Noodles 70g",
        "barcode": "8901058852462",
        "format": zxingcpp.BarcodeFormat.EAN13,
        "bg_color": (255, 235, 120),
        "accent_color": (210, 30, 30)
    },
    {
        "sku": "SKU-RICE-1KG",
        "name": "Fortune Basmati Rice 1kg",
        "barcode": "8906007280129",
        "format": zxingcpp.BarcodeFormat.EAN13,
        "bg_color": (245, 240, 230),
        "accent_color": (180, 140, 60)
    },
    {
        "sku": "SKU-OIL-1L",
        "name": "Fortune Sunflower Oil 1L",
        "barcode": "8906007281010",
        "format": zxingcpp.BarcodeFormat.EAN13,
        "bg_color": (255, 245, 200),
        "accent_color": (200, 140, 20)
    },
    {
        "sku": "SKU-SOAP-100",
        "name": "Dettol Original Soap 100g",
        "barcode": "8901396381006",
        "format": zxingcpp.BarcodeFormat.EAN13,
        "bg_color": (230, 250, 235),
        "accent_color": (40, 140, 70)
    }
]

for p in packs:
    img = Image.new("RGB", (600, 450), color=p["bg_color"])
    draw = ImageDraw.Draw(img)
    # Header branding
    draw.rectangle([0, 0, 600, 70], fill=p["accent_color"])
    draw.text((20, 25), p["name"], fill=(255, 255, 255))
    draw.text((20, 85), "SKU: " + p["sku"], fill=(50, 50, 50))
    
    # Generate optical barcode
    bc = zxingcpp.create_barcode(p["barcode"], p["format"])
    bc_arr = np.array(zxingcpp.write_barcode_to_image(bc))
    bc_img = Image.fromarray(bc_arr).resize((320, 150))
    
    # Paste barcode in white box
    draw.rectangle([130, 180, 470, 370], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
    img.paste(bc_img, (140, 190))
    draw.text((180, 345), p["barcode"], fill=(0, 0, 0))
    
    filename = f"{p['sku']}_{p['barcode']}.png"
    path = os.path.join(out_dir, filename)
    img.save(path)
    print(f"Saved {path}")

# Loose produce: no barcode, visual match only
loose_img = Image.new("RGB", (600, 450), color=(235, 245, 230))
draw = ImageDraw.Draw(loose_img)
draw.rectangle([0, 0, 600, 70], fill=(60, 120, 60))
draw.text((20, 25), "Fresh Loose Farm Apples (Unpacked)", fill=(255, 255, 255))
draw.text((20, 90), "SKU: SKU-PRODUCE-LOOSE", fill=(50, 50, 50))
draw.rectangle([100, 160, 500, 350], fill=(220, 240, 220), outline=(100, 160, 100), width=2)
draw.text((120, 240), "NO BARCODE - VISUAL MATCH ONLY", fill=(80, 120, 80))
loose_path = os.path.join(out_dir, "SKU-PRODUCE-LOOSE_no_barcode.png")
loose_img.save(loose_path)
print(f"Saved {loose_path}")
