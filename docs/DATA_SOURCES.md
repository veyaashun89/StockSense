# StockSense AI — Data Sources & Licencing Registry

This document lists all data sources, external APIs, pre-trained weights, and datasets utilized by StockSense AI, along with their respective licences, attribution requirements, and operational compliance constraints.

---

## 1. Data Sources & Licencing Matrix

| Data Source / Component | Origin / Provider | Purpose | Licence / Terms | Attribution & Compliance Requirements |
|---|---|---|---|---|
| **Open Food Facts** | [Open Food Facts](https://world.openfoodfacts.org/) | Global barcode lookup (EAN-13, UPC), product names, brands, categories, and packaging images. | **Open Database Licence (ODbL 1.0)** | 1. Persistent attribution displayed in application footer: *"Product data sourced from Open Food Facts under ODbL 1.0"*, linking to `https://openfoodfacts.org/`.<br>2. Rate limit respected (polite client, max 1 req/sec).<br>3. Custom descriptive `User-Agent: StockSenseAI/2.0 (contact: info@stocksense.ai)`.<br>4. Local SQLite response caching (`open_food_facts_cache`) to prevent redundant calls. |
| **zxing-cpp** | [zxing-cpp / Zebra Crossing](https://github.com/zxing-cpp/zxing-cpp) | On-device 1D/2D optical barcode decoding (EAN-13, Code-128, QR Codes). | **Apache License 2.0** | Permissive open source. Copyright notices retained in dependencies and source headers. Zero cloud dependency (runs 100% locally on CPU). |
| **Ultralytics YOLOv8n** | [Ultralytics](https://github.com/ultralytics/ultralytics) | Base neural network backbone for visual object detection and bounding-box localization. | **GNU Affero General Public License v3.0 (AGPL-3.0)** | Model fine-tuned on custom retail SKU dataset and exported to offline ONNX format (`yolov8n_custom.onnx`) for edge inference without telemetry. |
| **StockSense Retail Dataset** | StockSense In-House Capture (Sessions A–F) | 400 annotated shop-floor retail images across 7 classes (person + 6 retail SKUs), captured under real store lighting conditions. | **Proprietary / Internal Application Data** | Split strictly by capture session (Sessions A-D Train, Session E Val, Session F Test). Zero random-frame leakage between splits. |
| **Store Inventory Ledger** | Local SQLite Database (`stocksense.db`) | Master catalog, transaction logs, stock deductions, and double-entry inventory audit trail. | **Proprietary / Store Owner Ledger** | All currency values stored in integer paise. Strict `inventory_movements` table audit tracking with `owner_id`, `movement_type`, `delta`, and `balance_after`. |
| **Manual / Team CSV Fallback** | Store Manager / Inventory Admin | Bulk product import fallback when barcodes are unlisted in Open Food Facts or offline. | **Internal Operational Data** | Validated via `import_products_from_csv` with automatic stock movement ledger logging. |

---

## 2. Open Food Facts ODbL Compliance Details

StockSense AI adheres strictly to the Open Food Facts terms of use and the **Open Database Licence (ODbL)**:

1. **Attribution**:
   - Every product fetched or imported from Open Food Facts preserves its external reference.
   - The application frontend displays a persistent attribution footer across all pages:
     `Product data sourced from Open Food Facts under the Open Database Licence (ODbL 1.0)`.
2. **Database Rights & Share-Alike**:
   - Any modifications or derived open datasets adhere to the share-alike terms of ODbL.
   - Internal merchant sales records, pricing rules, and proprietary inventory levels remain strictly private to the merchant's SQLite ledger and are never conflated with public database records.
3. **Network Politeness & Caching**:
   - Backend queries are routed through `backend/services/open_food_facts_service.py`.
   - The service enforces a minimum delay of 1.0 second between consecutive requests to prevent load on Open Food Facts servers.
   - Lookups are cached indefinitely in SQLite table `open_food_facts_cache` with columns `(barcode, raw_json, cached_at)` to eliminate redundant network traffic.

---

## 3. Real Data vs. Seeded Demo Data Guarantee

As per system non-negotiable rules:
- **Live Sales & Inward Logistics**: Only real items scanned via barcode (zxing-cpp), recognized via multi-frame YOLO voting, or created through authenticated checkout endpoints are recorded to the live ledger.
- **Seeded Demo Scripts**: Hardcoded or synthetic demonstration datasets are strictly relegated to designated scripts (e.g., legacy migration or test generators) and prominently tagged with the `"Demo data"` badge and source attribution in the UI.
