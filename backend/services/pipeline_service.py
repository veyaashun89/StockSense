import os
import shutil
import datetime
from pathlib import Path
from typing import Dict, Any, List
from backend.database import get_db
from backend.services.gst_service import validate_and_preview_gst_csv, commit_gst_import
from backend.services.csv_service import validate_and_preview_sales_csv, commit_sales_import, import_products_csv
from backend.services.stock_service import ingest_stock_snapshot_csv
from backend.services.market_service import ingest_market_signals_csv
from backend.services.alert_service import evaluate_and_generate_alerts

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INBOX_DIR = BASE_DIR / "data_inbox"
PROCESSED_DIR = BASE_DIR / "data_processed"
REJECTED_DIR = BASE_DIR / "data_rejected"

def run_pipeline(triggered_by: str = "MANUAL", shop_id: int = 1) -> Dict[str, Any]:
    """
    Automated pipeline runner:
    1. Scans data_inbox/ for pending CSV files.
    2. Identifies file type and processes ingestion.
    3. Moves files to data_processed/ or data_rejected/.
    4. Triggers reorder planning and automated alert evaluation.
    5. Records log in pipeline_runs table.
    """
    db = get_db()
    cursor = db.cursor()

    INBOX_DIR.mkdir(exist_ok=True)
    PROCESSED_DIR.mkdir(exist_ok=True)
    REJECTED_DIR.mkdir(exist_ok=True)

    job_name = f"DATA_PIPELINE_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    started_at = datetime.datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO pipeline_runs (job_name, status, started_at, triggered_by)
        VALUES (?, 'RUNNING', ?, ?)
    """, (job_name, started_at, triggered_by))
    run_id = cursor.lastrowid
    db.commit()

    processed_files = []
    rejected_files = []
    total_processed_rows = 0
    total_rejected_rows = 0
    errors = []

    # Scan data_inbox/
    for file_path in INBOX_DIR.glob("*.csv"):
        filename = file_path.name
        timestamp_prefix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            first_line = content.splitlines()[0].lower() if content.splitlines() else ""

            # Detect CSV Type from headers
            if "invoice_no" in first_line and ("supply_type" in first_line or "gst" in first_line):
                # GST file
                res = validate_and_preview_gst_csv(content, filename, shop_id=shop_id)
                if res.get("valid_count", 0) > 0:
                    commit_gst_import(res["batch_id"], filename, res["all_valid"], shop_id=shop_id)
                    total_processed_rows += res["valid_count"]
                    total_rejected_rows += res["invalid_count"]
                    shutil.move(str(file_path), str(PROCESSED_DIR / f"{timestamp_prefix}{filename}"))
                    processed_files.append({"filename": filename, "type": "GST_INVOICES", "rows": res["valid_count"]})
                else:
                    total_rejected_rows += res.get("total_rows", 1)
                    errors.append(f"GST file '{filename}' had no valid rows: {res.get('error', 'Validation error')}")
                    shutil.move(str(file_path), str(REJECTED_DIR / f"{timestamp_prefix}{filename}"))
                    rejected_files.append(filename)

            elif "quantity_on_hand" in first_line:
                # Stock Snapshot
                res = ingest_stock_snapshot_csv(content, filename, shop_id=shop_id)
                if res.get("status") == "success":
                    total_processed_rows += res.get("reconciled_products", 0)
                    shutil.move(str(file_path), str(PROCESSED_DIR / f"{timestamp_prefix}{filename}"))
                    processed_files.append({"filename": filename, "type": "STOCK_SNAPSHOT", "rows": res.get("reconciled_products", 0)})
                else:
                    errors.append(f"Stock file '{filename}' error: {res.get('error')}")
                    shutil.move(str(file_path), str(REJECTED_DIR / f"{timestamp_prefix}{filename}"))
                    rejected_files.append(filename)

            elif "signal_type" in first_line or "festival_flag" in first_line:
                # Market Signals
                res = ingest_market_signals_csv(content)
                if res.get("status") == "success":
                    total_processed_rows += res.get("inserted_count", 0)
                    shutil.move(str(file_path), str(PROCESSED_DIR / f"{timestamp_prefix}{filename}"))
                    processed_files.append({"filename": filename, "type": "MARKET_SIGNALS", "rows": res.get("inserted_count", 0)})
                else:
                    errors.append(f"Market file '{filename}' error: {res.get('error')}")
                    shutil.move(str(file_path), str(REJECTED_DIR / f"{timestamp_prefix}{filename}"))
                    rejected_files.append(filename)

            elif "unit_cost" in first_line and "selling_price" in first_line:
                # Products Master Data
                res = import_products_csv(content)
                total_processed_rows += res.get("inserted", 0) + res.get("updated", 0)
                shutil.move(str(file_path), str(PROCESSED_DIR / f"{timestamp_prefix}{filename}"))
                processed_files.append({"filename": filename, "type": "PRODUCTS_MASTER", "rows": res.get("inserted", 0) + res.get("updated", 0)})

            else:
                # Standard Sales CSV
                res = validate_and_preview_sales_csv(content, filename)
                if res.get("valid_count", 0) > 0:
                    commit_sales_import(res["batch_id"], filename, res["all_valid"])
                    total_processed_rows += res["valid_count"]
                    total_rejected_rows += res["invalid_count"]
                    shutil.move(str(file_path), str(PROCESSED_DIR / f"{timestamp_prefix}{filename}"))
                    processed_files.append({"filename": filename, "type": "SALES_CSV", "rows": res["valid_count"]})
                else:
                    total_rejected_rows += res.get("total_rows", 1)
                    errors.append(f"Sales file '{filename}' had no valid rows: {res.get('error', 'Validation error')}")
                    shutil.move(str(file_path), str(REJECTED_DIR / f"{timestamp_prefix}{filename}"))
                    rejected_files.append(filename)

        except Exception as e:
            errors.append(f"Exception processing file '{filename}': {str(e)}")
            shutil.move(str(file_path), str(REJECTED_DIR / f"{timestamp_prefix}{filename}"))
            rejected_files.append(filename)

    # Automated Event-Triggered Recompute: Evaluate Alert Rules
    alert_res = evaluate_and_generate_alerts(shop_id=shop_id)

    status_str = "SUCCESS" if not errors else "PARTIAL_SUCCESS" if processed_files else "FAILED"
    finished_at = datetime.datetime.now().isoformat()
    error_summary = " | ".join(errors) if errors else None

    cursor.execute("""
        UPDATE pipeline_runs SET
            status = ?, finished_at = ?, rows_processed = ?,
            rows_rejected = ?, errors = ?
        WHERE id = ?
    """, (status_str, finished_at, total_processed_rows, total_rejected_rows, error_summary, run_id))
    db.commit()

    return {
        "run_id": run_id,
        "job_name": job_name,
        "status": status_str,
        "started_at": started_at,
        "finished_at": finished_at,
        "files_processed_count": len(processed_files),
        "files_rejected_count": len(rejected_files),
        "processed_files": processed_files,
        "rejected_files": rejected_files,
        "rows_processed": total_processed_rows,
        "rows_rejected": total_rejected_rows,
        "alerts_evaluated": alert_res,
        "errors": errors
    }

def get_latest_pipeline_status() -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT 1
    """)
    latest = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status = 'SUCCESS'")
    success_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status = 'FAILED'")
    failed_count = cursor.fetchone()[0]

    return {
        "latest_run": dict(latest) if latest else None,
        "total_successful_runs": success_count,
        "total_failed_runs": failed_count,
        "inbox_path": str(INBOX_DIR),
        "processed_path": str(PROCESSED_DIR),
        "rejected_path": str(REJECTED_DIR)
    }

def list_pipeline_runs(limit: int = 20) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(r) for r in cursor.fetchall()]
