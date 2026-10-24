import json
import pytest
from backend.app import create_app
from backend.services.notifier import get_ntfy_topic, mask_topic

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c

def test_get_notifications_list(client):
    res = client.get("/api/notifications")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "notifications" in data
    assert isinstance(data["notifications"], list)
    assert "total" in data

def test_get_notification_settings(client):
    res = client.get("/api/notifications/settings")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "settings" in data
    rules = [s["rule"] for s in data["settings"]]
    assert "low_stock" in rules
    assert "payment_verified" in rules

def test_update_notification_settings_validation(client):
    # Invalid time format
    res_bad_time = client.put("/api/notifications/settings", json={
        "rule": "low_stock",
        "quiet_hours_start": "25:99",
        "quiet_hours_end": "07:00"
    })
    assert res_bad_time.status_code == 400
    assert "24-hour HH:MM format" in res_bad_time.get_json()["error"]

    # Invalid rule name
    res_bad_rule = client.put("/api/notifications/settings", json={
        "rule": "unknown_fantasy_rule",
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00"
    })
    assert res_bad_rule.status_code == 400

    # Valid update
    res_good = client.put("/api/notifications/settings", json=[{
        "rule": "low_stock",
        "enabled": True,
        "threshold": 12.0,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "06:00",
        "min_minutes_between": 45
    }])
    assert res_good.status_code == 200
    assert res_good.get_json()["updated_count"] == 1

def test_test_send_rate_limiting(client):
    # First send should succeed
    res1 = client.post("/api/notifications/test-send")
    assert res1.status_code == 200
    assert res1.get_json()["status"] == "success"

    # Immediate second send within 60s should return 429
    res2 = client.post("/api/notifications/test-send")
    assert res2.status_code == 429
    assert "Rate limit exceeded" in res2.get_json()["error"]

def test_topic_info_secrecy(client):
    res = client.get("/api/notifications/topic-info")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"

    raw_topic = get_ntfy_topic()
    masked = mask_topic(raw_topic)

    assert data["masked_topic"] == masked
    # Full topic must NEVER be leaked in the response!
    assert raw_topic not in data["masked_topic"] or len(raw_topic) <= 4
    assert raw_topic not in json.dumps(data) or len(raw_topic) <= 4
    assert "instructions" in data
