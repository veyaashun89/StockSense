import sqlite3
import os
import shutil
import datetime
import hashlib
from contextlib import contextmanager
from pathlib import Path
from flask import g, has_app_context
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import Config
from backend.models.orm_models import Base

# Ensure parent directory for database exists
db_path = Path(Config.DATABASE)
db_path.parent.mkdir(parents=True, exist_ok=True)

# SQLAlchemy 2.x Engine
sqlite_url = f"sqlite:///{Config.DATABASE}"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False, "timeout": 15},
    echo=False
)

# Enforce connection PRAGMAs on every connection
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_engine() -> Engine:
    """Returns the SQLAlchemy Engine instance."""
    return engine

@contextmanager
def get_db_session():
    """
    Transactional context manager for SQLAlchemy ORM sessions.
    Automatically rolls back on uncaught exception and closes on completion.
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def hash_password(password: str) -> str:
    """Deterministic secure hash for demo users."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_db():
    """
    Flask context database accessor (backward-compatible with existing sqlite3 row queries).
    Enforces WAL mode, foreign keys, and 5000ms busy timeout.
    """
    if has_app_context():
        if "db" not in g:
            g.db = sqlite3.connect(Config.DATABASE, timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
            g.db.execute("PRAGMA journal_mode = WAL;")
            g.db.execute("PRAGMA busy_timeout = 5000;")
            g.db.execute("PRAGMA synchronous = NORMAL;")
        return g.db
    else:
        return get_standalone_db()

def get_standalone_db():
    """For scripts or test runners outside Flask application context."""
    conn = sqlite3.connect(Config.DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def backup_database(destination_dir: str = "backend/data/backups") -> str:
    """
    Performs an online, zero-downtime SQLite backup using sqlite3.backup API.
    Guarantees WAL logs are properly checkpointed and backed up.
    """
    dest_path = Path(destination_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = dest_path / f"stocksense_backup_{timestamp}.db"

    source_conn = sqlite3.connect(Config.DATABASE)
    dest_conn = sqlite3.connect(str(backup_file))
    try:
        with dest_conn:
            source_conn.backup(dest_conn, pages=250, sleep=0.01)
    finally:
        source_conn.close()
        dest_conn.close()

    return str(backup_file)

def get_schema_version() -> str:
    """Returns database schema version for health checks."""
    return "2.1.0-sqlalchemy-wal"

def init_db(drop_all=False):
    """
    Initializes all SQLAlchemy models, creates database tables,
    and seeds default system metadata (settings, default shop, demo users).
    """
    if drop_all:
        Base.metadata.drop_all(bind=engine)

    # Create all tables via SQLAlchemy ORM metadata
    Base.metadata.create_all(bind=engine)

    # Seed baseline shops, users, settings if missing
    db = get_standalone_db()
    cursor = db.cursor()

    # Default Settings
    default_settings = [
        ("lead_time_days", str(Config.DEFAULT_LEAD_TIME_DAYS), "Default supplier lead time in days"),
        ("safety_buffer_days", str(Config.DEFAULT_SAFETY_BUFFER_DAYS), "Default safety buffer in days"),
        ("coverage_days", str(Config.DEFAULT_COVERAGE_DAYS), "Default stock coverage horizon in days"),
        ("historical_window_days", str(Config.DEFAULT_HISTORICAL_WINDOW_DAYS), "Default sales history window in days"),
        ("forecast_horizon_days", str(Config.DEFAULT_FORECAST_HORIZON_DAYS), "Default forecast horizon in days"),
        ("forecast_horizon_weeks", "4", "Default forecast horizon in weeks"),
        ("currency", Config.DEFAULT_CURRENCY, "Store currency symbol"),
        ("budget", str(Config.DEFAULT_BUDGET), "Purchasing budget cap (0 for unlimited)"),
        ("forecast_method", Config.DEFAULT_FORECAST_METHOD, "Default forecast algorithm"),
        ("shelf_life_buffer_days", "2", "Minimum safety buffer before product expires"),
        ("stale_data_days_threshold", "3", "Days without new sales import before alerting"),
        ("enable_market_adjustment", "1", "Apply market signals"),
        ("retention_days", "30", "Detection events retention window in days"),
        ("blur_faces_default", "1", "Privacy face blurring default"),
        ("payment_timeout_minutes", "5", "Timeout for pending UPI checkout"),
        ("recording_timeout_minutes", "10", "Timeout for live camera recording session"),
    ]

    for key, val, desc in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
        """, (key, val, desc))

    # Ensure default shop exists
    cursor.execute("INSERT OR IGNORE INTO shops (id, name, address) VALUES (1, 'Apex Fresh Mart', 'Store #104, Central Market')")

    # Seed Default Users
    demo_users = [
        ("retailer@stocksense.in", hash_password("retailer123"), "retailer", "Ravi Sharma (Retailer)", 1),
        ("wholesaler@stocksense.in", hash_password("wholesaler123"), "wholesaler", "FreshValley Wholesale Supply", 1),
        ("dealer@stocksense.in", hash_password("dealer123"), "dealer", "Metro Regional Dealers Hub", 1),
        ("admin@stocksense.in", hash_password("admin123"), "admin", "System Administrator", 1),
        ("retailer@stocksense.ai", hash_password("retailer123"), "retailer", "Ravi Sharma (Retailer)", 1),
        ("wholesaler@stocksense.ai", hash_password("wholesaler123"), "wholesaler", "FreshValley Wholesale Supply", 1),
        ("dealer@stocksense.ai", hash_password("dealer123"), "dealer", "Metro Regional Dealers Hub", 1),
        ("admin@stocksense.ai", hash_password("admin123"), "admin", "System Administrator", 1),
    ]

    for email, pwd, role, name, shop_id in demo_users:
        cursor.execute("""
            INSERT OR IGNORE INTO users (email, password_hash, role, name, shop_id, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (email, pwd, role, name, shop_id))

    db.commit()
    db.close()
