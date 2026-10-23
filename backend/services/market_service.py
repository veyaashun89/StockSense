import csv
import io
import datetime
from typing import Dict, Any, List, Optional
from backend.database import get_db

def ingest_market_signals_csv(file_content: str) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()

    reader = csv.reader(io.StringIO(file_content.strip()))
    try:
        headers = [h.strip().lower() for h in next(reader, [])]
    except Exception as e:
        return {"error": str(e), "is_valid": False}

    required = {"date", "scope_type", "scope_value", "signal_type", "value"}
    if required - set(headers):
        return {"error": f"Missing required headers: {', '.join(sorted(required - set(headers)))}", "is_valid": False}

    d_idx = headers.index("date")
    st_idx = headers.index("scope_type")
    sv_idx = headers.index("scope_value")
    sig_idx = headers.index("signal_type")
    val_idx = headers.index("value")
    note_idx = headers.index("notes") if "notes" in headers else None

    inserted = 0
    for row in reader:
        if not row or not any(f.strip() for f in row):
            continue
        try:
            d = row[d_idx].strip()
            st = row[st_idx].strip().lower() # 'category' or 'sku'
            sv = row[sv_idx].strip()
            sig = row[sig_idx].strip()
            val = float(row[val_idx].strip())
            notes = row[note_idx].strip() if note_idx is not None and len(row) > note_idx else ""

            cursor.execute("""
                INSERT INTO market_signals (date, scope_type, scope_value, signal_type, value, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (d, st, sv, sig, val, notes))
            inserted += 1
        except Exception:
            continue

    db.commit()
    return {"status": "success", "inserted_count": inserted, "message": f"Successfully ingested {inserted} market signals."}

def get_active_market_multiplier(category: str, sku: str, target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns bounded market demand adjustment multiplier (clamped between 0.80 and 1.40).
    """
    db = get_db()
    cursor = db.cursor()

    # Check if market adjustment is enabled in settings
    cursor.execute("SELECT value FROM settings WHERE key = 'enable_market_adjustment'")
    s_row = cursor.fetchone()
    if s_row and s_row[0] == "0":
        return {"multiplier": 1.0, "is_adjusted": False, "notes": "Market adjustment disabled in settings"}

    cursor.execute("""
        SELECT scope_type, scope_value, signal_type, value, notes
        FROM market_signals
        WHERE (scope_type = 'sku' AND UPPER(scope_value) = ?)
           OR (scope_type = 'category' AND LOWER(scope_value) = ?)
        ORDER BY id DESC LIMIT 1
    """, (sku.upper(), category.lower()))
    
    row = cursor.fetchone()
    if not row:
        return {"multiplier": 1.0, "is_adjusted": False, "notes": "No active external market signal found (baseline unadjusted)"}

    raw_val = float(row["value"])
    # Strictly bound adjustment between 0.80 (-20%) and 1.40 (+40%)
    clamped_multiplier = max(0.80, min(1.40, raw_val))
    is_adjusted = abs(clamped_multiplier - 1.0) > 0.01

    return {
        "multiplier": round(clamped_multiplier, 3),
        "raw_signal_value": raw_val,
        "is_adjusted": is_adjusted,
        "signal_type": row["signal_type"],
        "notes": row["notes"] or f"Market signal applied: {row['signal_type']} (multiplier: {clamped_multiplier}x)"
    }
