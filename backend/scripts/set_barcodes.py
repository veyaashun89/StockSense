#!/usr/bin/env python3
"""
StockSense AI - Product Barcode Provisioning Utility
Reads a CSV of (sku, barcode), validates the EAN-13 check digit, refuses duplicates,
and updates the products table in the database.
"""
import sys
import os
import csv
import argparse
from typing import Dict, List, Set, Tuple

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database import get_db, init_db
from backend.app import create_app

def validate_ean13_check_digit(code: str) -> bool:
    """
    Validates the 13th check digit of an EAN-13 barcode using modulo-10 algorithm.
    Sum odd positions * 1, even positions * 3, subtract remainder from 10.
    """
    if len(code) != 13 or not code.isdigit():
        return False
    digits = [int(c) for c in code]
    # In 0-indexed positions: index 0 (1st) is weight 1, index 1 (2nd) is weight 3
    weighted_sum = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    remainder = weighted_sum % 10
    expected_check = (10 - remainder) % 10
    return expected_check == digits[12]

def set_barcodes(csv_path: str, verbose: bool = True) -> Dict[str, Any]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: List[Tuple[str, str]] = []
    seen_barcodes: Set[str] = set()

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        # Check if header exists
        if header and len(header) >= 2 and header[0].strip().lower() in ("sku", "id", "product_sku"):
            pass  # Header consumed
        elif header and len(header) >= 2:
            # Treat first row as data
            sku, bc = header[0].strip(), header[1].strip()
            rows.append((sku, bc))

        for line_num, r in enumerate(reader, start=2):
            if not r or len(r) < 2:
                continue
            sku, bc = r[0].strip(), r[1].strip()
            if not sku:
                continue
            rows.append((sku, bc))

    if not rows:
        raise ValueError("No valid rows found in CSV.")

    # 1. Validation phase (EAN-13 check digit and duplicate checks)
    validated_updates: List[Tuple[str, str]] = []
    for sku, bc in rows:
        # Check for empty / visual match only
        if not bc or bc.lower() in ("none", "missing", "visual_only", "no barcode"):
            validated_updates.append((sku, None))
            continue

        # Check for CSV duplicate
        if bc in seen_barcodes:
            raise ValueError(f"Duplicate barcode '{bc}' detected in CSV for SKU '{sku}'. Refusing import.")
        seen_barcodes.add(bc)

        # Validate EAN-13 if 13 digits
        if len(bc) == 13 and bc.isdigit():
            if not validate_ean13_check_digit(bc):
                digits = [int(c) for c in bc]
                weighted_sum = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
                expected = (10 - (weighted_sum % 10)) % 10
                raise ValueError(
                    f"Invalid EAN-13 check digit for SKU '{sku}' (barcode: {bc}). "
                    f"Provided check digit '{bc[-1]}', mathematically expected '{expected}'."
                )
        elif len(bc) not in (8, 12, 13) or not bc.isdigit():
            # Allow Code 128 / custom alphanumeric SKU barcodes or flag warning
            if verbose:
                print(f"[INFO] SKU {sku} uses non-EAN code: {bc}")

        validated_updates.append((sku, bc))

    # 2. Database application phase
    app = create_app({"TESTING": False})
    updated_records = []
    with app.app_context():
        init_db()
        db = get_db()
        cursor = db.cursor()

        for sku, bc in validated_updates:
            # Check if another product in DB already has this barcode
            if bc:
                cursor.execute(
                    "SELECT id, sku, name FROM products WHERE barcode = ? AND sku != ?",
                    (bc, sku)
                )
                conflict = cursor.fetchone()
                if conflict:
                    raise ValueError(
                        f"Barcode '{bc}' already assigned to SKU '{conflict['sku']}' ({conflict['name']}). "
                        f"Refusing duplicate assignment to SKU '{sku}'."
                    )

            # Update product
            cursor.execute(
                "UPDATE products SET barcode = ? WHERE sku = ?",
                (bc, sku)
            )
            affected = cursor.rowcount
            if affected > 0:
                updated_records.append({"sku": sku, "barcode": bc or "visual match only", "status": "updated"})
                if verbose:
                    print(f"[SUCCESS] Updated SKU '{sku}' -> Barcode: {bc or 'visual match only'}")
            else:
                if verbose:
                    print(f"[WARNING] SKU '{sku}' not found in database products table.")

        db.commit()

    return {
        "total_processed": len(rows),
        "total_updated": len(updated_records),
        "records": updated_records
    }

def main():
    parser = argparse.ArgumentParser(description="StockSense AI - Provision Product Barcodes from CSV")
    parser.add_argument("--csv", default=os.path.join(os.path.dirname(__file__), "..", "data", "barcodes.csv"), help="Path to input CSV")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose stdout output")
    args = parser.parse_args()

    try:
        res = set_barcodes(args.csv, verbose=not args.quiet)
        print(f"\nCompleted! Processed {res['total_processed']} rows, updated {res['total_updated']} products in DB.")
    except Exception as e:
        print(f"\n[ERROR] Failed to set barcodes: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
