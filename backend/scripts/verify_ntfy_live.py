import os
import sys
import time
import secrets
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.services.notifier import (
    send_ntfy_request,
    mask_topic,
    validate_ntfy_url,
    get_ntfy_base_url,
    get_ntfy_topic
)

def run_live_verification():
    print("=" * 70)
    print(" StockSense AI - Live ntfy.sh Verification & Latency Benchmark")
    print("=" * 70)

    # 1. Topic Secrecy Configuration
    current_topic = os.environ.get("NTFY_TOPIC")
    if not current_topic or current_topic == "stocksense-ops-alerts-default":
        # Generate high-entropy unguessable secret topic
        random_suffix = secrets.token_hex(8)
        current_topic = f"stocksense-live-{random_suffix}"
        os.environ["NTFY_TOPIC"] = current_topic

    base_url = get_ntfy_base_url()
    masked = mask_topic(current_topic)

    print(f"[1] Server Base URL  : {base_url}")
    print(f"[2] Masked Secret    : {masked} (Full secret topic is never displayed or logged)")
    print(f"[3] HTTPS Validation : {validate_ntfy_url(base_url)}")

    print("\n" + "-" * 70)
    print(" [Benchmark 1] Triggering Real Event 1: Low Stock Alert (Priority 3)")
    print("-" * 70)

    t0 = time.perf_counter()
    res1 = send_ntfy_request(
        message="Organic Almond Milk 1L low: 3 units left at Store-1 (reorder point: 5).",
        title="Low Stock: Organic Almond Milk",
        priority=3,
        tags="warning,package",
        topic=current_topic,
        base_url=base_url
    )
    t1 = time.perf_counter()
    latency1_ms = (t1 - t0) * 1000.0

    print(f"Status Code        : {res1.get('status_code')}")
    print(f"Delivery State     : {res1.get('status')}")
    print(f"Server Target      : {base_url}/{masked}")
    print(f"Roundtrip Latency  : {latency1_ms:.2f} ms ({latency1_ms/1000.0:.3f} seconds)")

    print("\n" + "-" * 70)
    print(" [Benchmark 2] Triggering Real Event 2: Critical Webhook Alert (Priority 5 Urgent)")
    print("-" * 70)

    t2 = time.perf_counter()
    res2 = send_ntfy_request(
        message="Security Alert: Incoming PaymentGateway webhook rejected. Reason category: INVALID_HMAC_SIGNATURE.",
        title="Critical: Webhook Verification Failed",
        priority=5,
        tags="rotating_light,skull",
        topic=current_topic,
        base_url=base_url
    )
    t3 = time.perf_counter()
    latency2_ms = (t3 - t2) * 1000.0

    print(f"Status Code        : {res2.get('status_code')}")
    print(f"Delivery State     : {res2.get('status')}")
    print(f"Server Target      : {base_url}/{masked}")
    print(f"Roundtrip Latency  : {latency2_ms:.2f} ms ({latency2_ms/1000.0:.3f} seconds)")

    print("\n" + "=" * 70)
    print(" VERIFICATION SUMMARY")
    print("=" * 70)
    avg_latency = (latency1_ms + latency2_ms) / 2.0
    print(f"Low-Stock Notification Delivery Time  : {latency1_ms:.1f} ms ({latency1_ms/1000.0:.2f}s)")
    print(f"Urgent Security Alert Delivery Time   : {latency2_ms:.1f} ms ({latency2_ms/1000.0:.2f}s)")
    print(f"Average API Dispatch Latency          : {avg_latency:.1f} ms ({avg_latency/1000.0:.2f}s)")
    print(f"Meets Requirement (< 10 seconds)      : {'YES - PASS' if avg_latency < 10000 else 'FAIL'}")
    print("=" * 70)

    return {
        "success": res1.get("status") == "sent" and res2.get("status") == "sent",
        "latency_low_stock_ms": latency1_ms,
        "latency_urgent_ms": latency2_ms,
        "avg_latency_ms": avg_latency,
        "masked_topic": masked
    }

if __name__ == "__main__":
    run_live_verification()
