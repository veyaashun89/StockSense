import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "stocksense.db"
DATABASE_PATH = os.environ.get("STOCKSENSE_DB", str(DEFAULT_DB_PATH))

class Config:
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    DATABASE = DATABASE_PATH
    SECRET_KEY = os.environ.get("SECRET_KEY", "stocksense-secret-key-quantix2026")
    
    # Inventory planning defaults
    DEFAULT_LEAD_TIME_DAYS = 7
    DEFAULT_SAFETY_BUFFER_DAYS = 3
    DEFAULT_COVERAGE_DAYS = 14
    DEFAULT_HISTORICAL_WINDOW_DAYS = 30
    DEFAULT_FORECAST_HORIZON_DAYS = 14
    DEFAULT_CURRENCY = "$"
    DEFAULT_BUDGET = 0.0  # 0 or None means unlimited
    DEFAULT_FORECAST_METHOD = "moving_average"  # 'moving_average' or 'linear_trend'
