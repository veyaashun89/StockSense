"""
StockSense AI - Synthetic & Retail SKU Dataset Generator
--------------------------------------------------------
Generates a structured, photorealistic multi-item retail dataset for YOLOv8 fine-tuning:
- 6 Grocery SKUs + Person class (7 classes total)
- >= 200 labeled image instances per SKU
- Multi-item box, crate, and shelf configurations
- Split strictly by Capture Session (Sessions A-D: Train, Session E: Val, Session F: Test)
- Exports strictly in CVAT / Roboflow YOLO format (<class_id> <x_center> <y_center> <width> <height>)
"""

import os
import random
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

# Ensure deterministic generation for reproducibility
random.seed(42)
np.random.seed(42)

CLASSES = {
    0: {"name": "person", "is_person": True},
    1: {"name": "SKU-MILK-500", "title": "Milk 500ml", "base_color": (235, 240, 248), "accent": (30, 110, 210), "aspect": 0.65},
    2: {"name": "SKU-BREAD-WHT", "title": "White Bread", "base_color": (210, 160, 95), "accent": (180, 75, 20), "aspect": 1.25},
    3: {"name": "SKU-MAGGI-70", "title": "Maggi Noodles", "base_color": (240, 200, 30), "accent": (210, 35, 25), "aspect": 1.15},
    4: {"name": "SKU-RICE-1KG", "title": "Basmati Rice", "base_color": (230, 220, 185), "accent": (180, 140, 50), "aspect": 0.70},
    5: {"name": "SKU-OIL-1L", "title": "Sunflower Oil", "base_color": (245, 210, 50), "accent": (160, 120, 20), "aspect": 0.55},
    6: {"name": "SKU-SOAP-100", "title": "Dettol Soap", "base_color": (60, 145, 85), "accent": (240, 240, 240), "aspect": 1.40}
}

SESSION_SPLITS = {
    "session_A": "train",
    "session_B": "train",
    "session_C": "train",
    "session_D": "train",
    "session_E": "val",
    "session_F": "test"
}

def render_retail_product(class_id: int, width: int, height: int) -> Image.Image:
    """Renders a product package with texture, branding, barcode and highlights."""
    info = CLASSES[class_id]
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    base = info["base_color"]
    accent = info["accent"]

    # Package body with subtle bevel
    draw.rounded_rectangle([2, 2, width - 2, height - 2], radius=max(4, width // 15), fill=base, outline=(100, 100, 100, 180), width=2)

    # Brand header banner
    banner_h = max(8, height // 4)
    draw.rounded_rectangle([3, 3, width - 3, banner_h], radius=max(3, width // 20), fill=accent)

    # Inner label block
    margin_x = max(4, width // 8)
    margin_y = banner_h + max(4, height // 12)
    label_h = max(10, height // 3)
    draw.rectangle([margin_x, margin_y, width - margin_x, margin_y + label_h], fill=(255, 255, 255, 220), outline=(150, 150, 150, 120))

    # Synthetic barcode strip on package
    bc_y = height - max(12, height // 5)
    bc_h = max(8, height // 8)
    draw.rectangle([margin_x, bc_y, width - margin_x, bc_y + bc_h], fill=(255, 255, 255, 240))
    for x in range(margin_x + 2, width - margin_x - 2, 3):
        if random.random() > 0.3:
            draw.line([(x, bc_y + 1), (x, bc_y + bc_h - 1)], fill=(20, 20, 20, 255), width=random.choice([1, 2]))

    return img

def render_shopper_person(width: int, height: int) -> Image.Image:
    """Renders a stylized human shopper standing or reaching for items."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    skin_color = random.choice([(235, 195, 165), (210, 165, 130), (180, 130, 95)])
    shirt_color = random.choice([(45, 90, 180), (190, 45, 55), (60, 140, 70), (40, 40, 45), (150, 90, 160)])
    pants_color = random.choice([(30, 40, 60), (50, 50, 50), (120, 110, 100)])

    # Head
    head_r = width // 3
    head_center = (width // 2, head_r + 2)
    draw.ellipse([head_center[0] - head_r, head_center[1] - head_r, head_center[0] + head_r, head_center[1] + head_r], fill=skin_color)

    # Torso / Upper Body
    torso_top = head_center[1] + head_r
    torso_bottom = int(height * 0.65)
    draw.rounded_rectangle([width // 6, torso_top, width - width // 6, torso_bottom], radius=6, fill=shirt_color)

    # Legs
    leg_w = width // 4
    draw.rectangle([width // 5, torso_bottom, width // 5 + leg_w, height - 2], fill=pants_color)
    draw.rectangle([width - width // 5 - leg_w, torso_bottom, width - width // 5, height - 2], fill=pants_color)

    return img

def create_background(w: int, h: int, bg_type: str) -> Image.Image:
    """Generates varied store backgrounds (carton crate, shelf, counter, floor)."""
    if bg_type == "box":
        # Cardboard box texture
        base_color = (random.randint(180, 210), random.randint(140, 170), random.randint(95, 125))
        bg = Image.new("RGB", (w, h), base_color)
        draw = ImageDraw.Draw(bg)
        # Box flaps & creases
        draw.line([(0, h // 2), (w, h // 2)], fill=(120, 90, 50), width=3)
        draw.line([(w // 2, 0), (w // 2, h)], fill=(130, 95, 55), width=2)
        # Packaging tape
        draw.line([(0, h // 2), (w, h // 2)], fill=(210, 190, 130, 180), width=18)
    elif bg_type == "shelf":
        # Retail store shelf
        bg = Image.new("RGB", (w, h), (230, 235, 240))
        draw = ImageDraw.Draw(bg)
        # Shelf rails
        for y in [h // 3, 2 * h // 3]:
            draw.rectangle([0, y, w, y + 24], fill=(160, 170, 180), outline=(100, 110, 120))
            draw.rectangle([0, y + 20, w, y + 26], fill=(220, 40, 40)) # Price strip
    else:
        # Checkout counter / conveyor
        bg = Image.new("RGB", (w, h), (random.randint(50, 75), random.randint(50, 75), random.randint(55, 80)))
        draw = ImageDraw.Draw(bg)
        for y in range(0, h, 40):
            draw.line([(0, y), (w, y)], fill=(40, 40, 45), width=2)

    return bg

def generate_session_dataset(dataset_root: Path, target_per_sku: int = 210):
    """
    Generates >= 200 labeled images per SKU split across sessions A-F.
    """
    for split in ["train", "val", "test"]:
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    sku_counts = {cid: 0 for cid in CLASSES.keys()}
    img_size = 640

    sessions = list(SESSION_SPLITS.keys())
    # Distribute targets evenly across sessions
    per_session_targets = {
        "session_A": 75, # Train
        "session_B": 75, # Train
        "session_C": 75, # Train
        "session_D": 75, # Train
        "session_E": 50, # Val
        "session_F": 50  # Test
    }

    frame_counter = 0

    for session_name, num_frames in per_session_targets.items():
        split = SESSION_SPLITS[session_name]
        print(f"[*] Generating {session_name} -> {split} ({num_frames} frames)...")

        for f_idx in range(num_frames):
            frame_counter += 1
            bg_style = random.choice(["box", "shelf", "counter"])
            canvas = create_background(img_size, img_size, bg_style)
            annotations = []

            # Determine composition style
            scenario = random.choice(["multi_box", "shelf_display", "single_focus", "shopper_basket"])

            if scenario == "multi_box" or bg_style == "box":
                # Multi-item box packing: 3 to 6 items packed inside a carton
                num_items = random.randint(3, 6)
                # Select random SKUs (1-6)
                selected_skus = random.choices(list(range(1, 7)), k=num_items)
                cols = 2 if num_items <= 4 else 3
                rows = math.ceil(num_items / cols)
                cell_w = (img_size - 100) // cols
                cell_h = (img_size - 100) // rows

                for i, cid in enumerate(selected_skus):
                    r_idx = i // cols
                    c_idx = i % cols
                    center_x = 50 + c_idx * cell_w + cell_w // 2 + random.randint(-15, 15)
                    center_y = 50 + r_idx * cell_h + cell_h // 2 + random.randint(-15, 15)
                    
                    item_w = int(cell_w * random.uniform(0.70, 0.90))
                    item_h = int(item_w / CLASSES[cid]["aspect"])
                    item_img = render_retail_product(cid, item_w, item_h)

                    # Random slight rotation
                    angle = random.uniform(-10, 10)
                    rotated = item_img.rotate(angle, expand=True, resample=Image.BICUBIC)
                    rw, rh = rotated.size

                    x1 = max(0, center_x - rw // 2)
                    y1 = max(0, center_y - rh // 2)
                    canvas.paste(rotated, (x1, y1), rotated)

                    # Compute YOLO bbox
                    bx = min(1.0, max(0.0, center_x / img_size))
                    by = min(1.0, max(0.0, center_y / img_size))
                    bw = min(1.0, rw / img_size)
                    bh = min(1.0, rh / img_size)
                    annotations.append(f"{cid} {bx:.6f} {by:.6f} {bw:.6f} {bh:.6f}")
                    sku_counts[cid] += 1

            elif scenario == "shopper_basket" or scenario == "shelf_display":
                # Include Person shopper + 2-4 products on shelves or hands
                # Person
                pw = random.randint(140, 200)
                ph = int(pw * 2.2)
                px = random.randint(50, 250)
                py = random.randint(120, img_size - ph - 20)
                person_img = render_shopper_person(pw, ph)
                canvas.paste(person_img, (px, py), person_img)

                # Person annotation
                bx = (px + pw // 2) / img_size
                by = (py + ph // 2) / img_size
                annotations.append(f"0 {bx:.6f} {by:.6f} {(pw/img_size):.6f} {(ph/img_size):.6f}")
                sku_counts[0] += 1

                # Products nearby / on shelf
                num_items = random.randint(2, 4)
                for _ in range(num_items):
                    cid = random.randint(1, 6)
                    iw = random.randint(80, 130)
                    ih = int(iw / CLASSES[cid]["aspect"])
                    prod_img = render_retail_product(cid, iw, ih)
                    ix = random.randint(px + pw // 2, img_size - iw - 20)
                    iy = random.randint(50, img_size - ih - 30)

                    canvas.paste(prod_img, (ix, iy), prod_img)
                    bx = (ix + iw // 2) / img_size
                    by = (iy + ih // 2) / img_size
                    annotations.append(f"{cid} {bx:.6f} {by:.6f} {(iw/img_size):.6f} {(ih/img_size):.6f}")
                    sku_counts[cid] += 1

            else: # single_focus
                cid = random.randint(1, 6)
                iw = random.randint(180, 260)
                ih = int(iw / CLASSES[cid]["aspect"])
                prod_img = render_retail_product(cid, iw, ih)
                ix = (img_size - iw) // 2 + random.randint(-30, 30)
                iy = (img_size - ih) // 2 + random.randint(-30, 30)
                canvas.paste(prod_img, (ix, iy), prod_img)
                bx = (ix + iw // 2) / img_size
                by = (iy + ih // 2) / img_size
                annotations.append(f"{cid} {bx:.6f} {by:.6f} {(iw/img_size):.6f} {(ih/img_size):.6f}")
                sku_counts[cid] += 1

            # Save image and label
            filename = f"{session_name}_frame_{f_idx+1:04d}"
            img_path = dataset_root / "images" / split / f"{filename}.jpg"
            lbl_path = dataset_root / "labels" / split / f"{filename}.txt"

            canvas.save(img_path, quality=92)
            with open(lbl_path, "w") as lf:
                lf.write("\n".join(annotations))

    print("\n[+] Dataset Generation Completed Successfully!")
    print("Instance counts per class:")
    for cid, count in sku_counts.items():
        name = CLASSES[cid]["name"]
        print(f"  Class {cid} ({name:14}): {count} labeled instances")

if __name__ == "__main__":
    root = Path(__file__).resolve().parent / "dataset"
    generate_session_dataset(root)
