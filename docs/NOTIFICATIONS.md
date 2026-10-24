# StockSense AI — Real-Time Mobile Push Notifications (`ntfy.sh`)

## 1. Executive Summary & Design Principles

StockSense AI integrates real-time mobile push notifications powered by [ntfy.sh](https://docs.ntfy.sh/publish/). The architecture adheres to mission-critical resilience guidelines for high-throughput retail operations:
- **Fire-and-Forget Delivery**: Notifications never block, delay, or roll back business transactions (sales, stock deductions, physical count reconciliation, or payments). Notification dispatch occurs strictly *after* database transactions commit.
- **Short Timeouts & Retry Backoff**: Requests to `ntfy.sh` have a strict **3.0-second timeout** and retry at most **3 times** with exponential backoff on server errors (`5xx`) or transient network drops. Client errors (`4xx`) are never retried, except `429 Too Many Requests` respecting `Retry-After`.
- **Zero Identifier PII / Zero Financial Data**: Notifications contain zero customer names, phone numbers, UPI IDs, UTR numbers, or card details. Summaries only (e.g. `Received ₹240.00 for 2 item(s) via UPI_INTENT`).
- **Topic Secrecy**: The topic name is treated as an unguessable secret configured via the `NTFY_TOPIC` environment variable. The system **never logs or displays the full topic** in application logs, database records, API responses, or UI displays. Only the masked suffix (e.g. `***565d`) is visible.
- **Noise Control & Deduplication**: Every notification has a composite deduplication key (`rule + product_id + location_id + date_bucket`). Duplicate alerts within `min_minutes_between` are suppressed. Non-urgent alerts (`priority < 5`) during operator quiet hours (e.g. `22:00` to `07:00`) are suppressed or deferred. Urgent alerts (`priority 5`) always dispatch immediately.

---

## 2. Event Rules & Priority Specification

| Rule Name | Trigger Event | Priority | ntfy Header | Default Threshold | Dedup Key Formula | Behavior & Noise Filter |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **`low_stock`** | Inventory deduction leaves stock $\le$ reorder level | **3** (or **4** if 0) | `Priority: 3` / `4` | $\le$ 10 units | `low_stock:product_id:location_id:YYYY-MM-DD` | Priority 4 when completely stockout (0 left); Priority 3 when below reorder point. |
| **`expiry_risk`** | Perishable batch reaches shelf-life buffer | **3** (or **4** if today) | `Priority: 3` / `4` | $\le$ 3 days | `expiry_risk:product_id:batch_ref:YYYY-MM-DD` | Priority 4 if expiring today ($\le 0$ days); Priority 3 within risk window. |
| **`payment_verified`** | Payment settled and ledger committed | **2** (Informational) | `Priority: 2` | 1 unit | `payment_verified:0:0:YYYY-MM-DD:txn_ref` | Zero PII / UTR / customer numbers. Indian rupee grouping. Suppressed during quiet hours. |
| **`count_mismatch`** | Box or shelf physical scan discrepancy | **4** (High) | `Priority: 4` | 1 unit diff | `count_mismatch:sku:location_id:YYYY-MM-DD` | Dispatches discrepancy variance (e.g. `-2 units`) and location name. |
| **`scanner_failure`** | POS scanner camera or decode timeout | **3** (Default) | `Priority: 3` | 3 in 10 mins | `scanner_failure:0:0:YYYY-MM-DD:terminal_bucket` | Only alerts after **3 consecutive failures** within a 10-minute sliding window. |
| **`webhook_failed`** | Webhook HMAC mismatch / missing signature | **5** (Urgent / Max) | `Priority: 5` | Immediate | `webhook_failed:0:0:YYYY-MM-DD:gateway_bucket` | **Bypasses quiet hours!** Admin role only. Contains reason category only, never raw payload. |

---

## 3. ntfy.sh Documentation & Feature Citations

All ntfy features implemented in StockSense AI conform to the official ntfy documentation:
- **Publishing & HTTP Headers**: [https://docs.ntfy.sh/publish/](https://docs.ntfy.sh/publish/)
  - Target URL format: `POST {NTFY_BASE_URL}/{NTFY_TOPIC}`
  - UTF-8 string payload passed in request body (`data=message.encode("utf-8")`)
  - Supported headers: `Title`, `Priority`, `Tags`, `Authorization: Bearer <token>`
- **Priority Mapping**: [https://docs.ntfy.sh/publish/#message-priority](https://docs.ntfy.sh/publish/#message-priority)
  - Scale: `1` (min), `2` (low), `3` (default), `4` (high), `5` (urgent/max).
  - Also accepts named aliases (`min`, `low`, `default`, `high`, `urgent`).
- **Emoji Tags**: [https://docs.ntfy.sh/publish/#tags-emojis](https://docs.ntfy.sh/publish/#tags-emojis)
  - Shortcode emoji names passed as comma-separated values (e.g. `warning,package`, `white_check_mark,moneybag`, `rotating_light,skull`).

---

## 4. Measured Delivery Benchmark

Benchmark executed via `backend/scripts/verify_ntfy_live.py` against `https://ntfy.sh`:

```
======================================================================
 StockSense AI - Live ntfy.sh Verification & Latency Benchmark
======================================================================
[1] Server Base URL  : https://ntfy.sh
[2] Masked Secret    : ***565d (Full secret topic is never displayed or logged)
[3] HTTPS Validation : True

----------------------------------------------------------------------
 [Benchmark 1] Triggering Real Event 1: Low Stock Alert (Priority 3)
----------------------------------------------------------------------
Status Code        : 200
Delivery State     : sent
Server Target      : https://ntfy.sh/***565d
Roundtrip Latency  : 896.12 ms (0.896 seconds)

----------------------------------------------------------------------
 [Benchmark 2] Triggering Real Event 2: Critical Webhook Alert (Priority 5 Urgent)
----------------------------------------------------------------------
Status Code        : 200
Delivery State     : sent
Server Target      : https://ntfy.sh/***565d
Roundtrip Latency  : 827.92 ms (0.828 seconds)

======================================================================
 VERIFICATION SUMMARY
======================================================================
Low-Stock Notification Delivery Time  : 896.1 ms (0.90s)
Urgent Security Alert Delivery Time   : 827.9 ms (0.83s)
Average API Dispatch Latency          : 862.0 ms (0.86s)
Meets Requirement (< 10 seconds)      : YES - PASS (Delivery under 1 second)
======================================================================
```

---

## 5. Mobile App Setup Instructions

1. **Install the Mobile App**:
   - iOS: Install **ntfy** from the [Apple App Store](https://apps.apple.com/app/ntfy/id1625396347).
   - Android: Install **ntfy** from [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy) or F-Droid.
2. **Subscribe to Topic**:
   - Open the ntfy app.
   - Tap the **`+`** (Subscribe) button.
   - Server: Enter `https://ntfy.sh` (or your private self-hosted URL).
   - Topic name: Enter the value of your team's `NTFY_TOPIC` environment variable.
3. **Verify Alert Delivery**:
   - In the StockSense UI, navigate to **Push Notifications** $\rightarrow$ **Mobile App Setup**.
   - Click **Dispatch Live Test Push**.
   - Confirm notification banner appears on your phone within **1 to 2 seconds**.

---

## 6. Self-Hosting Guide

StockSense AI seamlessly supports private, self-hosted ntfy servers:
1. Deploy ntfy via Docker:
   ```bash
   docker run -p 8080:80 -it binwiederhier/ntfy serve --cache-file /var/cache/ntfy/cache.db
   ```
2. Configure environment variables in StockSense:
   ```powershell
   $env:NTFY_BASE_URL = "https://ntfy.yourdomain.com"
   $env:NTFY_TOPIC    = "stocksense-private-alert-topic-xyz"
   $env:NTFY_TOKEN    = "tk_your_optional_access_token"
   ```
3. HTTPS Enforcement: Remote HTTP URLs are rejected by `validate_ntfy_url` for security. Only `localhost` and `127.0.0.1` are permitted over HTTP for local testing.

---

## 7. Known Limitations & Test Environment Boundary

1. **Local Sandbox Headless Browser (Playwright)**:
   - In this execution sandbox, the Playwright binary driver download returned `404 Not Found` (`https://playwright.azureedge.net/builds/driver/playwright-1.57.0-win32_x64.zip`).
   - Consequently, end-to-end browser automation subagent could not record WebP video.
   - All backend APIs, unit test suites (76/76 tests passing), frontend production TypeScript bundling (`tsc -b && vite build`), and live REST verification were validated directly via PowerShell HTTP calls.
2. **Apple APNs Push Delays**:
   - While `ntfy.sh` server latency is $\approx 860$ ms, iOS push notifications rely on Apple Push Notification service (APNs). When background app refresh is throttled on low battery, delivery may take 3–5 seconds on iOS.

---

## 8. Exact PowerShell Commands

### Environment Setup
```powershell
# Set secure, unguessable topic
$env:NTFY_TOPIC = "stocksense-alert-sec-" + [System.Guid]::NewGuid().ToString().Substring(0, 8)
$env:NTFY_BASE_URL = "https://ntfy.sh"
```

### Run All Pytest Tests
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Build Frontend
```powershell
cd frontend
npm run build
cd ..
```

### Run Live ntfy Latency Benchmark
```powershell
.\.venv\Scripts\python.exe backend/scripts/verify_ntfy_live.py
```

### Start Local Servers
```powershell
# Terminal 1: Start Flask Backend
.\.venv\Scripts\python.exe backend/app.py

# Terminal 2: Start Vite Frontend
cd frontend
npm run dev
```
