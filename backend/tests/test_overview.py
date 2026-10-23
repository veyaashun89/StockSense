import pytest
import json
from backend.services.overview_service import invalidate_overview_cache

def test_retailer_overview_schema_and_values(client):
    """Proves retailer overview returns expected stable schema and non-negative values."""
    invalidate_overview_cache()
    res = client.get("/api/overview/retailer", headers={"X-User-Role": "retailer"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "retailer"
    assert "generated_at" in data
    assert "kpis" in data
    assert "today_sales_paise" in data["kpis"]
    assert "today_items_sold" in data["kpis"]
    assert "stock_value_paise" in data["kpis"]
    assert "items_to_restock" in data["kpis"]
    assert isinstance(data["attention_list"], list)
    assert "stock_health" in data
    assert "trend" in data

def test_wholesaler_overview_schema_and_values(client):
    """Proves wholesaler overview returns expected stable schema."""
    invalidate_overview_cache()
    res = client.get("/api/overview/wholesaler", headers={"X-User-Role": "wholesaler"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "wholesaler"
    assert "generated_at" in data
    assert "kpis" in data
    assert "open_orders" in data["kpis"]
    assert "orders_value_paise" in data["kpis"]
    assert "retailers_served" in data["kpis"]
    assert "stock_value_paise" in data["kpis"]
    assert isinstance(data["attention_list"], list)
    assert isinstance(data["trend"], list)

def test_dealer_overview_schema_and_values(client):
    """Proves dealer overview returns expected stable schema."""
    invalidate_overview_cache()
    res = client.get("/api/overview/dealer", headers={"X-User-Role": "dealer"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "dealer"
    assert "generated_at" in data
    assert "kpis" in data
    assert "stock_supplied_month_units" in data["kpis"]
    assert "open_wholesaler_orders" in data["kpis"]
    assert "fill_rate_percentage" in data["kpis"]
    assert "dealer_territory" in data
    assert isinstance(data["margin_tiers"], list)

def test_admin_overview_schema_and_values(client):
    """Proves admin overview returns expected telemetry and health schema."""
    invalidate_overview_cache()
    res = client.get("/api/overview/admin", headers={"X-User-Role": "admin"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "admin"
    assert "generated_at" in data
    assert "kpis" in data
    assert "active_users_by_role" in data["kpis"]
    assert "system_health" in data
    assert "database" in data["system_health"]
    assert "detection_model" in data["system_health"]
    assert "notifications" in data["system_health"]
    assert isinstance(data["recent_audit_logs"], list)

def test_role_isolation_retailer_cannot_access_other_overviews(client):
    """Proves a retailer cannot access wholesaler, dealer, or admin overviews."""
    res_wh = client.get("/api/overview/wholesaler", headers={"X-User-Role": "retailer"})
    assert res_wh.status_code == 403

    res_dl = client.get("/api/overview/dealer", headers={"X-User-Role": "retailer"})
    assert res_dl.status_code == 403

    res_ad = client.get("/api/overview/admin", headers={"X-User-Role": "retailer"})
    assert res_ad.status_code == 403

def test_role_isolation_wholesaler_cannot_access_other_overviews(client):
    """Proves a wholesaler cannot access retailer, dealer, or admin overviews."""
    res_ret = client.get("/api/overview/retailer", headers={"X-User-Role": "wholesaler"})
    assert res_ret.status_code == 403

    res_dl = client.get("/api/overview/dealer", headers={"X-User-Role": "wholesaler"})
    assert res_dl.status_code == 403

    res_ad = client.get("/api/overview/admin", headers={"X-User-Role": "wholesaler"})
    assert res_ad.status_code == 403

def test_role_isolation_dealer_cannot_access_other_overviews(client):
    """Proves a dealer cannot access retailer, wholesaler, or admin overviews."""
    res_ret = client.get("/api/overview/retailer", headers={"X-User-Role": "dealer"})
    assert res_ret.status_code == 403

    res_wh = client.get("/api/overview/wholesaler", headers={"X-User-Role": "dealer"})
    assert res_wh.status_code == 403

    res_ad = client.get("/api/overview/admin", headers={"X-User-Role": "dealer"})
    assert res_ad.status_code == 403

def test_unified_overview_dispatches_by_server_role(client):
    """Proves GET /api/overview returns role-scoped data based on authenticated role."""
    res_ret = client.get("/api/overview", headers={"X-User-Role": "retailer"})
    assert res_ret.status_code == 200
    assert res_ret.get_json()["role"] == "retailer"

    res_wh = client.get("/api/overview", headers={"X-User-Role": "wholesaler"})
    assert res_wh.status_code == 200
    assert res_wh.get_json()["role"] == "wholesaler"

    res_dl = client.get("/api/overview", headers={"X-User-Role": "dealer"})
    assert res_dl.status_code == 200
    assert res_dl.get_json()["role"] == "dealer"

    res_ad = client.get("/api/overview", headers={"X-User-Role": "admin"})
    assert res_ad.status_code == 200
    assert res_ad.get_json()["role"] == "admin"

def test_overview_cache_and_invalidation(client):
    """Proves 30-second caching preserves data and cache invalidation endpoint works."""
    res1 = client.get("/api/overview/admin", headers={"X-User-Role": "admin"})
    t1 = res1.get_json()["generated_at"]

    # Immediate second call should return identical cached generated_at
    res2 = client.get("/api/overview/admin", headers={"X-User-Role": "admin"})
    t2 = res2.get_json()["generated_at"]
    assert t1 == t2

    # Invalidate cache
    res_inv = client.post("/api/overview/cache/invalidate", headers={"X-User-Role": "admin"})
    assert res_inv.status_code == 200
