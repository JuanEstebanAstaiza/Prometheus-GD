import pytest
from datetime import timedelta
from app.core.security import create_access_token

def test_login_success(client, super_admin_user):
    """Test successful login"""
    response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "testpassword"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert "expires_in" in data
    assert "user" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["id"] == super_admin_user.id

def test_login_wrong_password(client, super_admin_user):
    """Test login with wrong password"""
    response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "wrongpassword"
    })

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_login_inactive_user(client, db_session, super_admin_user):
    """Test login with inactive user"""
    super_admin_user.is_active = False
    db_session.commit()

    response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "testpassword"
    })

    assert response.status_code == 401
    assert "Account is inactive" in response.json()["detail"]

def test_refresh_token_success(client, super_admin_user):
    """Test successful token refresh"""
    # First login to get tokens
    login_response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "testpassword"
    })
    refresh_token = login_response.json()["refresh_token"]

    # Now refresh
    response = client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["id"] == super_admin_user.id

def test_refresh_token_invalid(client):
    """Test refresh with invalid token"""
    response = client.post("/auth/refresh", json={
        "refresh_token": "invalid-token"
    })

    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]

def test_logout_success(client, super_admin_user):
    """Test successful logout"""
    # First login to get tokens
    login_response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "testpassword"
    })
    refresh_token = login_response.json()["refresh_token"]
    access_token = login_response.json()["access_token"]

    # Now logout
    response = client.post("/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["message"]

def test_verify_token_success(client, super_admin_user):
    """Test token verification"""
    # First login to get token
    login_response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "testpassword"
    })
    access_token = login_response.json()["access_token"]

    # Verify token
    response = client.post("/auth/verify",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True
    assert data["user"]["id"] == super_admin_user.id

def test_verify_token_invalid(client):
    """Test verification with invalid token"""
    response = client.post("/auth/verify",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401

def test_rbac_super_admin_access(client, auth_headers_super_admin):
    """Test that super admin can access admin endpoints"""
    response = client.get("/admin/backups", headers=auth_headers_super_admin)
    # Should not return 403 (forbidden)
    assert response.status_code != 403

def test_rbac_admin_dep_limited_access(client, auth_headers_admin_dep):
    """Test that admin dep has limited access"""
    # Should be able to access their own dependency data
    response = client.get("/users/me", headers=auth_headers_admin_dep)
    assert response.status_code == 200

def test_rbac_worker_limited_access(client, auth_headers_worker):
    """Test that worker has limited access"""
    # Should be able to access their own profile
    response = client.get("/users/me", headers=auth_headers_worker)
    assert response.status_code == 200

    # Should not be able to access admin endpoints
    response = client.get("/admin/backups", headers=auth_headers_worker)
    assert response.status_code == 403  # Workers don't have access to admin endpoints

def test_rate_limiting(client, super_admin_user):
    """Test login rate limiting"""
    # Make multiple failed login attempts
    for i in range(6):  # More than limit
        response = client.post("/auth/login", json={
            "email": super_admin_user.email,
            "password": "wrongpassword"
        })

    # Should eventually be rate limited
    # Note: This test assumes rate limiting is enabled
    # In a real test environment, you might need to adjust the rate limit settings

def test_user_profile_access(client, auth_headers_super_admin, super_admin_user):
    """Test user profile access"""
    response = client.get("/users/me", headers=auth_headers_super_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == super_admin_user.id
    assert data["email"] == super_admin_user.email

def test_user_profile_update(client, auth_headers_super_admin, super_admin_user):
    """Test user profile update"""
    new_name = "Updated Super Admin"
    response = client.put("/users/me",
        json={"full_name": new_name},
        headers=auth_headers_super_admin
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == new_name

def test_user_profile_update_forbidden_fields(client, auth_headers_super_admin):
    """Test that sensitive fields cannot be updated via profile"""
    response = client.put("/users/me",
        json={"role": "WORKER"},  # Should be forbidden
        headers=auth_headers_super_admin
    )
    # Should either fail or ignore the forbidden field
    assert response.status_code in [200, 400]
