# StockSense AI v2: REST API Documentation
> Base URL: `http://127.0.0.1:5000/api`  
> Format: JSON  
> Role-Based Access Control enforced on all endpoints.

---

## 1. Authentication & Roles (`/api/auth`)

### `POST /api/auth/login`
Authenticate user with email and password.
- **Request**: `{"email": "retailer@stocksense.in", "password": "retailer123"}`
- **Response** `(200 OK)`:
  ```json
  {
    "user": {
      "id": 1,
      "email": "retailer@stocksense.in",
      "name": "Lakshmi Stores",
      "role": "retailer",
      "shop_id": 1,
      "token": "sess-..."
    },
    "message": "Login successful"
  }
  ```

### `POST /api/auth/switch-role`
Switch demo active role for hackathon evaluation.
- **Request**: `{"role": "wholesaler"}` | `"retailer"` | `"admin"`
- **Response** `(200 OK)`: User object for selected role.

### `GET /api/auth/me`
Return current authenticated session user and role.

---

## 2. Inventory & Master Data (`/api/products`)

### `GET /api/products`
List inventory items with pagination, category filter, and search.
- **Parameters**: `search`, `category`, `status`, `page`, `per_page`
- **Response** `(200 OK)`:
  ```json
  {
    "total": 30,
    "page": 1,
    "per_page": 50,
    "items": [
      {
        "id": 1,
        "sku": "MLK-001",
        "name": "Fresh Cow Milk 1L",
        "category": "Dairy & Bakery",
        "current_stock": 8,
        "unit_cost": 42.0,
        "selling_price": 54.0,
        "lead_time_days": 1,
        "shelf_life_days": 3,
        "is_perishable": 1,
        "min_order_qty": 10,
        "pack_size": 5,
        "safety_buffer_days": 1
      }
    ]
  }
  ```

### `POST /api/products`
Add new product to master catalog.

---

## 3. Data Ingestion Hub

### `POST /api/sales/validate` & `POST /api/sales/import`
Pre-flight CSV validation and transactional commit for historical sales.
- **Columns**: `sku,sale_date,quantity_sold`

### `POST /api/gst/validate` & `POST /api/gst/import`
Pre-flight validation and commit for GST tax invoices.
- **Columns**: `invoice_no,invoice_date,supply_type,gstin_counterparty,hsn_code,item_description,sku,quantity,taxable_value,gst_rate,total_value`
- **Commit Payload**:
  ```json
  {
    "batch_id": "gst-batch-...",
    "filename": "gst_invoices.csv",
    "valid_rows": [...],
    "update_stock": true
  }
  ```

### `GET /api/gst/lines` & `POST /api/gst/mappings`
Retrieve parsed GST invoice lines and create HSN/keyword to SKU mappings.

### `POST /api/stock/import` & `GET /api/stock/batches`
Ingest on-hand stock snapshots with batch IDs and expiry dates; reconcile inventory movements.

### `POST /api/market/import` & `GET /api/market`
Ingest external market trend signals (festivals, price indices, localized demand spikes).

---

## 4. Forecasting Engine (`/api/forecast`)

### `GET /api/forecast`
Compute daily empirical demand forecast and held-out backtest evaluation.
- **Parameters**: `product_id`, `horizon` (days), `window` (sampling days), `method` (`moving_average` or `linear_trend`)
- **Response** `(200 OK)`:
  ```json
  {
    "product_id": 1,
    "sku": "MLK-001",
    "product_name": "Fresh Cow Milk 1L",
    "average_daily_demand": 24.5,
    "lead_time_demand": 25,
    "trend_direction": "increasing",
    "trend_slope": 0.35,
    "evaluation": {
      "mae": 2.1,
      "rmse": 3.4,
      "test_window_days": 7
    },
    "historical_series": [...],
    "daily_forecast": [...]
  }
  ```

### `GET /api/forecast/weekly`
Compute ISO weekly-bucketed demand predictions with lower/upper range bounds.
- **Parameters**: `product_id`, `horizon_weeks` (4 to 12), `window` (days)
- **Response** `(200 OK)`:
  ```json
  {
    "product_id": 1,
    "avg_weekly_demand": 172.0,
    "weekly_forecast": [
      {
        "week_number": 1,
        "week_start": "2026-10-27",
        "predicted_units": 172,
        "lower_bound": 148,
        "upper_bound": 196,
        "range_label": "±14% Range"
      }
    ]
  }
  ```

---

## 5. Reorder Planner (`/api/reorder`)

### `GET /api/reorder`
Run replenishment calculation across all products, applying lead times, safety stocks, incoming POs, supplier packaging, and hard perishable shelf-life caps.
- **Parameters**: `category`, `priority`, `search`, `budget`
- **Response** `(200 OK)`:
  ```json
  {
    "summary": {
      "total_products": 30,
      "products_requiring_reorder": 14,
      "critical_stockouts": 4,
      "total_reorder_value": 38450.0,
      "total_reorder_units": 1120,
      "products_capped_by_shelf_life": 3
    },
    "items": [
      {
        "product_id": 1,
        "sku": "MLK-001",
        "name": "Fresh Cow Milk 1L",
        "priority": "CRITICAL",
        "current_stock": 8,
        "incoming_units": 0,
        "inventory_position": 8,
        "average_daily_demand": 24.5,
        "lead_time_demand": 25,
        "reorder_point": 50,
        "target_stock": 172,
        "recommended_reorder_qty": 35,
        "shelf_life_capped": true,
        "shelf_life_cap": 35,
        "usable_selling_window": 2,
        "purchase_cost": 1470.0,
        "recommendation_reason": "Days to stockout (0d) <= lead time (1d). Order capped to 35 units to prevent spoilage."
      }
    ]
  }
  ```

---

## 6. Purchase Orders (`/api/orders`)

### `GET /api/orders`
List purchase orders with optional status filter (`Submitted`, `Confirmed`, `Dispatched`, `Delivered`, `Cancelled`).

### `POST /api/orders`
Create a purchase order from reorder recommendations.
- **Request**:
  ```json
  {
    "items": [
      {"product_id": 1, "sku": "MLK-001", "product_name": "Fresh Cow Milk 1L", "quantity": 35, "unit_cost": 42.0}
    ],
    "notes": "Weekly store dairy replenishment"
  }
  ```

### `PATCH /api/orders/<id>/status`
Update status (Wholesaler confirms/dispatches; Retailer confirms delivery). On `Delivered`, stock automatically updates via `inventory_movements`.

---

## 7. Automated Alerts (`/api/alerts`)

### `GET /api/alerts`
Retrieve active and historical alerts.
- **Parameters**: `status` (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`), `severity`

### `PATCH /api/alerts/<id>`
Update alert status (`ACKNOWLEDGED` or `RESOLVED`).

### `POST /api/alerts/evaluate`
Trigger rule engine evaluation; creates deduplicated alerts and auto-resolves cleared conditions.

---

## 8. Wholesale Hub (`/api/wholesale`)

### `GET /api/wholesale/catalog` & `POST /api/wholesale/catalog`
Retrieve and manage wholesale SKUs, minimum order quantities, pack sizes, lead times, and available wholesale stock.

### `GET /api/wholesale/demand-signals`
Aggregated, anonymized weekly retail demand signals across connected stores to assist upstream supplier stocking.

---

## 9. Automated Pipeline (`/api/pipeline`)

### `GET /api/pipeline/status`
Check watched folder (`data_inbox/`) status, pending files, and last run outcome.

### `GET /api/pipeline/runs`
Audit history of pipeline executions.

### `POST /api/pipeline/run`
Trigger immediate pipeline scan, ingestion, recompute, and alert evaluation.

---

## 10. Admin Governance (`/api/admin`)

### `GET /api/admin/users`, `POST /api/admin/users`, `PATCH /api/admin/users/<id>`
User and role administration.

### `GET /api/admin/system`
System diagnostic health and entity counts.

---

## 11. AI Vision & Dynamic Payment Gateway (`/api/scanner` & `/api/payment`)

### `POST /api/scanner/recognize`
Computer Vision multi-modal product recognition from camera frame or image upload.
- **Payload**:
  ```json
  {
    "image": "data:image/jpeg;base64,...",
    "barcode_text": "SKU-MLK-01",
    "detected_label": "milk dairy"
  }
  ```
- **Response** `(200 OK)`:
  ```json
  {
    "matched": true,
    "confidence": 0.88,
    "confidence_percentage": "88%",
    "recognition_mode": "cv_feature_model",
    "product": {
      "id": 1,
      "sku": "SKU-MLK-01",
      "name": "Fresh Whole Milk 1 Gal",
      "category": "Dairy & Fresh",
      "current_stock": 6,
      "selling_price": 4.29,
      "is_perishable": 1,
      "shelf_life_days": 7
    },
    "bounding_box": [0.18, 0.22, 0.82, 0.78],
    "visual_signature": {
      "category_alignment": "Dairy & Fresh",
      "detected_dominant_rgb": [220, 225, 230],
      "edge_complexity": 0.42
    }
  }
  ```

### `POST /api/scanner/quick-sale`
Instant 1-unit (or custom quantity) retail sale with automated ledger deduction.
- **Payload**: `{"product_id": 1, "quantity": 1}`
- **Response** `(200 OK)`:
  ```json
  {
    "status": "success",
    "product_id": 1,
    "sku": "SKU-MLK-01",
    "name": "Fresh Whole Milk 1 Gal",
    "sold_quantity": 1,
    "new_stock": 5,
    "total_value": 4.29
  }
  ```

### `POST /api/scanner/quick-restock`
Quick inventory restock with batch ID and expiration date assignment.
- **Payload**: `{"product_id": 1, "quantity": 20, "batch_id": "RESTOCK-1023", "expiry_date": "2026-10-30"}`

### `POST /api/payment/generate-qr`
Generates a dynamic Indian UPI QR payment code encoded in standard vector SVG.
- **Payload**: `{"amount": 108.0, "purpose": "POS Supermarket Checkout", "order_id": "PO-1001"}`
- **Response** `(200 OK)`:
  ```json
  {
    "transaction_ref": "TXN-20261023-A89E10",
    "amount": 108.0,
    "currency": "INR",
    "currency_symbol": "₹",
    "upi_id": "stocksense.retail@upi",
    "merchant_name": "StockSense Retail Supermarket",
    "upi_uri": "upi://pay?pa=stocksense.retail@upi&pn=StockSense+Retail&am=108.00&cu=INR&tr=TXN-...",
    "qr_svg": "<svg xmlns=...>...</svg>",
    "status": "PENDING"
  }
  ```

### `POST /api/payment/verify`
Verifies payment receipt, records transactions to sales ledger, reconciles stock balance, and audits movement in `inventory_movements`.
- **Payload**:
  ```json
  {
    "transaction_ref": "TXN-20261023-A89E10",
    "amount": 108.0,
    "payment_method": "UPI_QR",
    "utr_number": "UTR-9912048291",
    "cart_items": [{"product_id": 1, "sku": "SKU-MLK-01", "quantity": 2}],
    "purchase_order_id": null
  }
  ```

---

## 8. Automated State Machine & Live Record Analytics (`/api/record`, `/api/session`)

### `GET /api/session/state`
Single source of truth for the retail checkout session state machine.
- **Response** `(200 OK)`:
  ```json
  {
    "session_id": 1,
    "session_uuid": "sess_bd120a91e5f2",
    "state": "RECORDING",
    "started_at": "2026-10-23T17:07:44.131349",
    "ended_at": null,
    "allowed_transitions": ["IDLE"],
    "transitions_count": 5
  }
  ```

### `POST /api/session/transition`
Execute an explicit state machine transition. Validates legal transitions (`IDLE -> SCANNING -> BASKET -> PAYMENT_PENDING -> PAID -> RECORDING -> IDLE`).
- **Payload**:
  ```json
  {
    "target_state": "RECORDING",
    "reason": "Checkout settled auto-transition",
    "session_id": 1
  }
  ```
- **Response** `(200 OK)`:
  ```json
  {
    "session_id": 1,
    "session_uuid": "sess_bd120a91e5f2",
    "state": "RECORDING",
    "allowed_transitions": ["IDLE"],
    "reason": "Checkout settled auto-transition",
    "timestamp": "2026-10-23T17:08:00.000000"
  }
  ```

### `POST /api/record/start`
Starts an automated object detection recording session and transitions state machine to `RECORDING`. Resets the centroid tracker.
- **Payload**: `{"operator_id": 1}`
- **Response** `(200 OK)`:
  ```json
  {
    "status": "recording",
    "session_id": 1,
    "session_uuid": "sess_bd120a91e5f2",
    "state": "RECORDING",
    "message": "Live object detection session initialized.",
    "privacy_notice": "Camera analytics: people are counted, not identified."
  }
  ```

### `POST /api/record/stop`
Finalizes the recording session, computes summary metrics, writes end timestamp to SQLite, and transitions state machine to `IDLE`.
- **Payload**: `{"session_id": 1}`
- **Response** `(200 OK)`:
  ```json
  {
    "status": "stopped",
    "session_id": 1,
    "state": "IDLE",
    "summary": {
      "session_id": 1,
      "unique_people_count": 4,
      "total_products_detected": 18,
      "matched_skus": ["SKU-MILK-500", "SKU-MAGGI-70"],
      "matched_skus_count": 2,
      "unmatched_items_count": 16,
      "total_events": 22
    },
    "message": "Session finalized. Stored metrics and returned to IDLE."
  }
  ```

### `GET /api/record/live`
Pollable live telemetry: returns active detections, session counters, detector FPS, and state machine state.
- **Response** `(200 OK)`:
  ```json
  {
    "status": "ok",
    "detector_ready": true,
    "measured_fps": 19.3,
    "last_inference_ms": 51.8,
    "counters": {
      "unique_people_session": 3,
      "unique_products_session": 5,
      "active_tracks_count": 4,
      "total_frames_processed": 142
    },
    "privacy_notice": "Camera analytics: people are counted, not identified.",
    "session": {
      "session_id": 1,
      "state": "RECORDING"
    }
  }
  ```

### `POST /api/record/frame`
Accepts a base64 JPEG from the webcam canvas, runs YOLOv8n ONNX inference on CPU, classifies persons and demo grocery SKUs, tracks bounding boxes with IoU tracker, and returns detections. Enforces maximum 1 MB payload restriction.
- **Payload**:
  ```json
  {
    "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "blur_faces": true,
    "session_id": 1
  }
  ```
- **Response** `(200 OK)`:
  ```json
  {
    "status": "success",
    "frame_width": 480,
    "frame_height": 360,
    "inference_time_ms": 48.2,
    "fps": 20.7,
    "people_in_frame": 1,
    "unique_people_session": 3,
    "products_in_frame": 2,
    "unique_products_session": 5,
    "matched_skus": ["SKU-MILK-500"],
    "detections": [
      {
        "class_name": "person",
        "confidence": 0.89,
        "track_id": 1,
        "bbox": [0.25, 0.15, 0.65, 0.85],
        "is_new": false
      },
      {
        "class_name": "product",
        "confidence": 0.86,
        "track_id": 4,
        "sku": "SKU-MILK-500",
        "sku_name": "Amul Taaza Milk 500ml",
        "bbox": [0.70, 0.40, 0.88, 0.72],
        "is_new": true
      }
    ],
    "privacy_notice": "Camera analytics: people are counted, not identified.",
    "annotated_frame": "data:image/jpeg;base64,..."
  }
  ```

### `GET /api/record/sessions`
Returns paginated list of archived recording sessions from SQLite.
- **Parameters**: `limit=20`

### `GET /api/record/sessions/{id}`
Returns granular history of a specific session including timeline of state transitions and detection events.

### `POST /api/payment/webhook`
Production payment webhook callback endpoint. Verifies HMAC-SHA256 signature in `X-StockSense-Signature` header. Reconciles inventory atomically and marks session `PAID`.
- **Headers**:
  - `Content-Type: application/json`
  - `X-StockSense-Signature: <hmac_sha256_hex_digest>`
- **Payload**:
  ```json
  {
    "transaction_ref": "TXN-20261023-A89E10",
    "amount": 108.0,
    "utr_number": "UTR-9912048291",
    "cart_items": [{"product_id": 1, "sku": "SKU-MLK-01", "quantity": 2}]
  }
  ```
- **Demo Mode**: Setting `X-Demo-Simulate: true` simulates the signed gateway webhook during live evaluation.

### `POST /api/record/purge-old-events`
Retention policy enforcement: purges detection events older than N days.
- **Payload**: `{"older_than_days": 30}`
- **Response** `(200 OK)`:
  ```json
  {
    "status": "success",
    "deleted_count": 1420,
    "retention_days": 30,
    "message": "Purged 1420 detection event records older than 30 days."
  }
  ```

### `GET /api/health`
Health check reporting system status, database connectivity, and SQLite Alembic schema revision.
- **Response** `(200 OK)`:
  ```json
  {
    "status": "healthy",
    "service": "StockSense Retail Inventory Intelligence API",
    "version": "2.1.0",
    "database": {
      "connected": true,
      "engine": "sqlite",
      "schema_version": "2.1.0-sqlalchemy-wal",
      "error": null
    },
    "timestamp": "2026-10-24T03:00:00.000000"
  }
  ```

---

## 10. Warehouse Locations & Box Scan (`/api/locations`)
Roles allowed: `wholesaler`, `retailer`, `admin` (Dealer forbidden: HTTP 403)

### `GET /api/locations`
Lists all physical storage hierarchy locations (shelves, bins, boxes) with stock and parent relationships.
- **Response** `(200 OK)`:
  ```json
  {
    "locations": [
      {
        "id": 1,
        "name": "Shelf A1 (Dairy Section)",
        "location_type": "shelf",
        "barcode": "LOC-SH-A1",
        "parent_id": null,
        "stock": [{"sku": "SKU-MLK-01", "expected_quantity": 40, "actual_quantity": 40, "status": "MATCH"}]
      }
    ],
    "total": 5
  }
  ```

### `POST /api/locations`
Creates a new physical location. Restricted to `wholesaler`, `admin`.
- **Payload**: `{"name": "Box BX-05", "location_type": "box", "barcode": "LOC-BX-05", "parent_id": 2}`

### `POST /api/locations/{id}/box-scan`
Runs box scan count reconciliation from image frame or direct count dictionary. Automatically detects shortages/surpluses and emits `LOCATION_MISMATCH` alert.
- **Payload**:
  ```json
  {
    "scanned_counts": {
      "SKU-MLK-01": 20
    }
  }
  ```
- **Response** `(200 OK)`:
  ```json
  {
    "status": "success",
    "reconciliation": {
      "location_id": 3,
      "location_name": "Box BX-01 (Amul Dairy Crate)",
      "total_skus_checked": 1,
      "mismatch_count": 1,
      "alerts_created": ["Location Count Mismatch in 'Box BX-01 (Amul Dairy Crate)'"],
      "reconciled_items": [
        {
          "sku": "SKU-MLK-01",
          "expected_quantity": 24,
          "actual_quantity": 20,
          "difference": -4,
          "status": "MISMATCH_SHORTAGE"
        }
      ]
    }
  }
  ```

---

## 11. Data Pipeline & Records History (`/api/records`)

### `POST /api/records/import/sales`
Imports sales records from CSV or Excel (`.xlsx`). Supports `?dry_run=true` to preview valid/rejected row counts without writing to SQLite.
- **Query Params**: `?dry_run=true` | `?dry_run=false`
- **Multipart Form**: `file: sales_oct.xlsx`
- **Response** `(200 OK)`:
  ```json
  {
    "status": "committed",
    "filename": "sales_oct.xlsx",
    "total_rows": 150,
    "imported_count": 148,
    "rejected_count": 2,
    "rejected_rows": [{"row_index": 12, "sku": "UNKNOWN_SKU", "reason": "Unknown SKU 'UNKNOWN_SKU'"}]
  }
  ```

### `POST /api/records/import/stock`
Imports on-hand stock snapshot from CSV or Excel. Strictly logs every delta to `inventory_movements` (Rule 5 compliance). Restricted to `wholesaler`, `admin`.

### `GET /api/records/sales`
Queries historical sales records aggregated by day or week.
- **Parameters**: `group_by=day` | `group_by=week`, `sku`, `limit=100`

### `GET /api/records/stock-movements`
Queries complete audit trail of inventory adjustments (`SALE`, `RESTOCK`, `IMPORT_SNAPSHOT`, `BOX_RECONCILIATION`).

### `GET /api/records/batches`
Lists all historical data load batches with import timestamp, row counts, and status.

---

## 12. Dealer & Regional Distributor (`/api/dealer`)
Roles allowed: `dealer`, `admin` (Retailer and Wholesaler forbidden: HTTP 403)

### `GET /api/dealer/dispatches`
Lists brand-level order dispatches, carrier tracking numbers, and transit status.

### `POST /api/dealer/dispatches`
Creates a brand-level dispatch order to a regional hub.
- **Payload**:
  ```json
  {
    "brand": "Amul Dairy Corp",
    "sku": "SKU-MLK-01",
    "units": 500,
    "region": "Maharashtra-Zone-1",
    "carrier": "BlueDart Express"
  }
  ```

### `GET /api/dealer/pricing-tiers`
Retrieves volume pricing tiers and wholesale discount matrices.

### `GET /api/dealer/allocations`
Retrieves regional inventory allocation breakdown across warehouse hubs.

---

## 13. Role Overview & Telemetry Summary (`/api/overview`)
Provides server-scoped, 30-second TTL cached overviews for each of the four system roles. Enforces strict RBAC (a retailer cannot access wholesaler/dealer/admin data).

### `GET /api/overview`
Unified role dispatcher: Inspects authenticated caller's role and returns that role's scoped overview.
- **Roles allowed**: `retailer`, `wholesaler`, `dealer`, `admin`
- **Response `(200 OK)`**: Scoped payload matching the authenticated role.

### `GET /api/overview/retailer`
Retailer store pulse and urgent action queue.
- **Roles allowed**: `retailer`, `admin` (Wholesaler & Dealer: HTTP 403)
- **Response `(200 OK)`**:
  ```json
  {
    "role": "retailer",
    "generated_at": "2026-10-24T04:36:00.000000",
    "kpis": {
      "today_sales_paise": 2485000,
      "today_items_sold": 42,
      "sales_change_pct": 14.8,
      "stock_value_paise": 18420000,
      "items_to_restock": 4,
      "total_reorder_units": 85
    },
    "attention_list": [
      {
        "id": "stockout-1",
        "severity": "critical",
        "title": "Immediate Stockout",
        "affected": "SKU-MLK-01",
        "message": "Amul Taaza Milk 1L has 0 units in stock.",
        "actionLabel": "Reorder SKU"
      }
    ],
    "stock_health": {
      "healthy": 26,
      "low": 3,
      "expiring": 0,
      "out_of_stock": 1,
      "total_skus": 30
    },
    "trend": [{"date": "2026-10-23", "value": 24850.0, "secondaryValue": 42}]
  }
  ```

### `GET /api/overview/wholesaler`
Wholesaler order pipeline and bulk stock valuation.
- **Roles allowed**: `wholesaler`, `admin` (Retailer & Dealer: HTTP 403)
- **Response `(200 OK)`**:
  ```json
  {
    "role": "wholesaler",
    "generated_at": "2026-10-24T04:36:00.000000",
    "kpis": {
      "open_orders": 2,
      "orders_value_paise": 1485000,
      "retailers_served": 4,
      "stock_value_paise": 48200000,
      "catalog_skus": 18
    },
    "attention_list": [...],
    "recent_orders": [...],
    "trend": [...]
  }
  ```

### `GET /api/overview/dealer`
Regional dealership allocation, quota fulfillment, and margin tiers.
- **Roles allowed**: `dealer`, `admin` (Retailer & Wholesaler: HTTP 403)
- **Response `(200 OK)`**:
  ```json
  {
    "role": "dealer",
    "generated_at": "2026-10-24T04:36:00.000000",
    "kpis": {
      "stock_supplied_month_units": 1450,
      "open_wholesaler_orders": 2,
      "fill_rate_percentage": 98.4,
      "regional_stock_allocated_units": 5200
    },
    "dealer_territory": "North-West Metropolitan District",
    "margin_tiers": [
      {"tier": "Tier 1: Staples & Grains", "margin": "8.5%", "status": "OPTIMAL"}
    ],
    "trend": [...]
  }
  ```

### `GET /api/overview/admin`
System-wide health telemetry, ML computer vision status, and security audit log.
- **Roles allowed**: `admin` only (Retailer, Wholesaler & Dealer: HTTP 403)
- **Response `(200 OK)`**:
  ```json
  {
    "role": "admin",
    "generated_at": "2026-10-24T04:36:00.000000",
    "kpis": {
      "active_users_by_role": {"retailer": 1, "wholesaler": 1, "dealer": 1, "admin": 1},
      "total_users": 4,
      "transactions_today": 12,
      "volume_today_paise": 1845000,
      "open_alerts": 0,
      "pipeline_runs": 8
    },
    "system_health": {
      "database": {"connected": true, "engine": "sqlite_wal", "schema_version": "30420276a191"},
      "detection_model": {"status": "ACTIVE", "model_name": "yolov8n_custom.onnx", "measured_fps": 15.0},
      "notifications": {"service": "ntfy.sh", "status": "CONNECTED", "topic": "stocksense-alerts"}
    },
    "recent_audit_logs": [...]
  }
  ```

### `POST /api/overview/cache/invalidate`
Clears in-memory 30-second TTL overview cache across all roles.
- **Roles allowed**: `admin`
- **Response `(200 OK)`**: `{"status": "invalidated", "message": "Overview cache cleared"}`




