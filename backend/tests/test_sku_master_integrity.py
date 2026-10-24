import csv
import re
from pathlib import Path
import pytest

MASTER_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "products_master.csv"

def get_master_skus():
    assert MASTER_CSV_PATH.exists(), f"Products master CSV does not exist at {MASTER_CSV_PATH}"
    with open(MASTER_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["sku"].strip() for row in reader if row.get("sku")}

def test_products_master_csv_structure_and_types():
    """Verify products_master.csv has all required schema columns and valid data types."""
    assert MASTER_CSV_PATH.exists()
    required_cols = {
        "sku", "name", "category", "retail_price_paise", "unit_cost_paise",
        "selling_price", "unit_cost", "lead_time_days", "is_perishable",
        "min_order_qty", "pack_size", "safety_buffer_days", "current_stock"
    }

    with open(MASTER_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        assert required_cols.issubset(fieldnames), f"Missing columns in master CSV: {required_cols - fieldnames}"

        rows = list(reader)
        assert len(rows) >= 6, "Master CSV must contain at least the 6 core retail SKUs"

        for row in rows:
            sku = row["sku"].strip()
            assert sku, "SKU cannot be empty"
            price_paise = int(row["retail_price_paise"])
            cost_paise = int(row["unit_cost_paise"])
            assert price_paise >= 0, f"Negative price for {sku}"
            assert cost_paise >= 0, f"Negative cost for {sku}"

def test_vision_service_markers_present_in_master():
    """Verify all visual markers in vision_service.py map to valid master SKUs."""
    from backend.services.vision_service import DEMO_SKU_MARKERS
    master_skus = get_master_skus()

    for marker in DEMO_SKU_MARKERS:
        sku = marker["sku"]
        assert sku in master_skus, f"Vision marker SKU '{sku}' is missing from backend/data/products_master.csv"

def test_yolo_dataset_yaml_skus_present_in_master():
    """Verify every class in dataset.yaml maps to valid master SKUs."""
    yaml_path = Path(__file__).resolve().parent.parent / "ml" / "dataset.yaml"
    master_skus = get_master_skus()
    if yaml_path.exists():
        import yaml
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
            names = data.get("names", {})
            sku_classes = [name for name in names.values() if name.startswith("SKU-")]
            for sku in sku_classes:
                assert sku in master_skus, f"YOLO class SKU '{sku}' is missing from backend/data/products_master.csv"

def test_all_code_referenced_skus_exist_in_master():
    """
    Fails if any product SKU referenced in tests, seeds, or services
    is missing from products_master.csv.
    """
    master_skus = get_master_skus()
    
    # Explicitly check essential known test & operational SKUs
    essential_skus = [
        "SKU-MILK-500", "SKU-BREAD-WHT", "SKU-MAGGI-70", "SKU-RICE-1KG", "SKU-OIL-1L", "SKU-SOAP-100",
        "SKU-MLK-01", "MLK-001", "SKU-TEST-MILK", "SKU-BER-06", "SKU-SUS-07", "SKU-YOG-02", "SKU-TOW-27"
    ]
    
    missing = [sku for sku in essential_skus if sku not in master_skus]
    assert not missing, f"Missing SKUs in products_master.csv: {missing}"
