import os
import sys
import subprocess
import time

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5000"

TARGETS = [
    ("retailer_overview", f"{BASE_URL}/?role=retailer"),
    ("wholesaler_overview", f"{BASE_URL}/orders?role=wholesaler"),
    ("dealer_overview", f"{BASE_URL}/?role=dealer"),
    ("admin_overview", f"{BASE_URL}/admin?role=admin"),
    ("scanner", f"{BASE_URL}/scanner"),
    ("record", f"{BASE_URL}/record"),
    ("inventory", f"{BASE_URL}/inventory"),
    ("data_management", f"{BASE_URL}/data"),
    ("alerts", f"{BASE_URL}/alerts"),
]

def capture(folder="docs/screenshots/before"):
    out_dir = os.path.abspath(folder)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"[*] Capturing screenshots to: {out_dir}")
    
    for name, url in TARGETS:
        # Desktop (1280x800)
        desk_path = os.path.join(out_dir, f"{name}_desktop.png")
        cmd_desk = [
            CHROME_BIN,
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=2000",
            f"--screenshot={desk_path}",
            "--window-size=1280,800",
            url
        ]
        subprocess.run(cmd_desk, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        desk_ok = os.path.exists(desk_path) and os.path.getsize(desk_path) > 0
        
        # Phone (360x740)
        phone_path = os.path.join(out_dir, f"{name}_phone.png")
        cmd_phone = [
            CHROME_BIN,
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=2000",
            f"--screenshot={phone_path}",
            "--window-size=360,740",
            url
        ]
        subprocess.run(cmd_phone, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        phone_ok = os.path.exists(phone_path) and os.path.getsize(phone_path) > 0
        
        print(f" -> {name}: Desktop={'OK' if desk_ok else 'FAIL'}, Phone={'OK' if phone_ok else 'FAIL'}")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/before"
    capture(folder)
