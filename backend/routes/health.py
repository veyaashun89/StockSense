import datetime
import sqlite3
from flask import Blueprint, jsonify
from backend.database import get_engine
from sqlalchemy import text

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    db_connected = False
    schema_version = "unknown"
    db_error = None

    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                db_connected = True
            
            # Fetch alembic version if available
            try:
                ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                if ver:
                    schema_version = str(ver)
                else:
                    schema_version = "30420276a191_initial"
            except Exception:
                schema_version = "v2.0.0"
    except Exception as e:
        db_error = str(e)

    status_str = "healthy" if db_connected else "degraded"
    status_code = 200 if db_connected else 503

    return jsonify({
        "status": status_str,
        "service": "StockSense Retail Inventory Intelligence API",
        "version": "2.0.0",
        "database": {
            "connected": db_connected,
            "engine": "sqlite",
            "schema_version": schema_version,
            "error": db_error
        },
        "timestamp": datetime.datetime.now().isoformat()
    }), status_code

