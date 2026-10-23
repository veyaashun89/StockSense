import pytest
from backend.services.auth_service import (
    authenticate_user, switch_demo_role, verify_token, check_tenant_access
)

def test_all_four_roles_authentication_and_tokens():
    """Verify retailer, wholesaler, dealer, and admin can all authenticate and have valid tokens."""
    roles = ["retailer", "wholesaler", "dealer", "admin"]
    for role in roles:
        user = switch_demo_role(role)
        assert user is not None, f"Failed to switch to role {role}"
        assert user["role"] == role
        assert "token" in user

        # Verify token contents
        payload = verify_token(user["token"])
        assert payload is not None
        assert payload["role"] == role

def test_dashboard_tailored_views_per_role(client):
    """Verify dashboard endpoint returns role-specific views for each of the 4 roles."""
    # 1. Retailer
    res = client.get("/api/dashboard", headers={"X-User-Role": "retailer"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "retailer"
    assert "summary" in data
    assert "top_urgent_products" in data

    # 2. Wholesaler
    res = client.get("/api/dashboard", headers={"X-User-Role": "wholesaler"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "wholesaler"
    assert "catalog_items" in data["summary"]
    assert "order_pipeline" in data

    # 3. Dealer
    res = client.get("/api/dashboard", headers={"X-User-Role": "dealer"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "dealer"
    assert "dealer_territory" in data
    assert "margin_tiers" in data

    # 4. Admin
    res = client.get("/api/dashboard", headers={"X-User-Role": "admin"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "admin"
    assert "summary" in data
    assert "active_users" in data["summary"]

def test_rbac_admin_endpoint_forbidden_for_non_admins(client):
    """Verify non-admin roles cannot access /admin/users and receive HTTP 403."""
    non_admin_roles = ["retailer", "wholesaler", "dealer"]
    for role in non_admin_roles:
        res = client.get("/api/admin/users", headers={"X-User-Role": role})
        assert res.status_code == 403, f"Expected 403 for role {role}, got {res.status_code}"
        assert "Forbidden" in res.get_json().get("error", "")

    # Admin access succeeds
    admin_res = client.get("/api/admin/users", headers={"X-User-Role": "admin"})
    assert admin_res.status_code == 200

def test_rbac_dealer_endpoints_forbidden_for_retailer_and_wholesaler(client):
    """Verify dealer endpoints are restricted to dealer and admin."""
    # Retailer blocked
    res = client.get("/api/dealer/dispatches", headers={"X-User-Role": "retailer"})
    assert res.status_code == 403

    # Wholesaler blocked
    res = client.get("/api/dealer/dispatches", headers={"X-User-Role": "wholesaler"})
    assert res.status_code == 403

    # Dealer allowed
    res = client.get("/api/dealer/dispatches", headers={"X-User-Role": "dealer"})
    assert res.status_code == 200
    assert "dispatches" in res.get_json()

    # Admin allowed
    res = client.get("/api/dealer/dispatches", headers={"X-User-Role": "admin"})
    assert res.status_code == 200

def test_rbac_dealer_cannot_access_store_locations(client):
    """Verify dealer cannot access internal warehouse/store locations (HTTP 403)."""
    res = client.get("/api/locations", headers={"X-User-Role": "dealer"})
    assert res.status_code == 403

    # Retailer and Wholesaler are allowed
    res_retailer = client.get("/api/locations", headers={"X-User-Role": "retailer"})
    assert res_retailer.status_code == 200

    res_wholesaler = client.get("/api/locations", headers={"X-User-Role": "wholesaler"})
    assert res_wholesaler.status_code == 200

def test_rbac_wholesaler_and_dealer_cannot_run_pos_quick_sale(client):
    """Verify retail POS quick-sale is forbidden for wholesaler and dealer."""
    payload = {"product_id": 1, "quantity": 1}

    # Wholesaler blocked
    res = client.post("/api/scanner/quick-sale", json=payload, headers={"X-User-Role": "wholesaler"})
    assert res.status_code == 403

    # Dealer blocked
    res = client.post("/api/scanner/quick-sale", json=payload, headers={"X-User-Role": "dealer"})
    assert res.status_code == 403

def test_tenant_access_isolation():
    """Verify check_tenant_access enforces strict isolation across users."""
    retailer_ctx = {"user_id": 1, "role": "retailer"}
    other_user_ctx = {"user_id": 2, "role": "retailer"}
    admin_ctx = {"user_id": 99, "role": "admin"}

    # Same owner access granted
    assert check_tenant_access(target_owner_id=1, current_user=retailer_ctx) is True

    # Cross-tenant access denied
    assert check_tenant_access(target_owner_id=2, current_user=retailer_ctx) is False
    assert check_tenant_access(target_owner_id=1, current_user=other_user_ctx) is False

    # Admin access granted universally
    assert check_tenant_access(target_owner_id=1, current_user=admin_ctx) is True
    assert check_tenant_access(target_owner_id=2, current_user=admin_ctx) is True

    # None context denied
    assert check_tenant_access(target_owner_id=1, current_user=None) is False

def test_invalid_bearer_token_unauthorized(client):
    """Verify invalid token string returns HTTP 401 Unauthorized."""
    res = client.get("/api/admin/users", headers={"Authorization": "Bearer totally_bogus_token"})
    assert res.status_code == 401
    assert "Unauthorized" in res.get_json().get("error", "")
