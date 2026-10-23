import time
import threading
from pathlib import Path

_scheduler_thread = None
_stop_event = threading.Event()

def start_background_watcher():
    """
    Starts a lightweight background watcher thread for data_inbox/
    Automatically processes dropped CSVs every 10 seconds.
    """
    global _scheduler_thread, _stop_event

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return

    _stop_event.clear()

    def watcher_loop():
        from backend.services.pipeline_service import INBOX_DIR, run_pipeline
        while not _stop_event.is_set():
            try:
                if INBOX_DIR.exists():
                    csv_files = list(INBOX_DIR.glob("*.csv"))
                    if csv_files:
                        # Found files to process!
                        run_pipeline(triggered_by="INBOX_WATCHER")
            except Exception as e:
                pass
            time.sleep(10)

    _scheduler_thread = threading.Thread(target=watcher_loop, daemon=True, name="StockSenseInboxWatcher")
    _scheduler_thread.start()

def stop_background_watcher():
    global _stop_event
    _stop_event.set()
