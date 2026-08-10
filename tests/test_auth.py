VALID_PASSWORD = "StrongP@ss1"


def register(client, email="user@example.com", password=VALID_PASSWORD):
    return client.post("/register", json={"email": email, "password": password})


def login(client, email="user@example.com", password=VALID_PASSWORD):
    return client.post("/login", json={"email": email, "password": password})


def test_register_success(client):
    response = register(client)
    assert response.status_code == 200
    assert "registered" in response.json()["message"]


def test_register_duplicate_email_rejected(client):
    register(client)
    response = register(client)
    assert response.status_code == 400


def test_register_weak_password_rejected(client):
    response = register(client, password="weak")
    assert response.status_code == 422


def test_login_success_returns_tokens(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(client):
    register(client)
    response = login(client, password="WrongP@ss1")
    assert response.status_code == 401


def test_login_unknown_email_rejected(client):
    response = login(client, email="nobody@example.com")
    assert response.status_code == 401


def test_refresh_rotates_token(client):
    register(client)
    tokens = login(client).json()

    response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    reuse_response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse_response.status_code == 401


def test_refresh_invalid_token_rejected(client):
    response = client.post("/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


def test_logout_revokes_token(client):
    register(client)
    tokens = login(client).json()

    response = client.post("/logout", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200

    reuse_response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse_response.status_code == 401


def test_protected_route_requires_valid_token(client):
    response = client.get("/translations")
    assert response.status_code in (401, 403)


def test_protected_route_rejects_garbage_token(client):
    response = client.get("/translations", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_protected_route_accepts_valid_token(client):
    register(client)
    tokens = login(client).json()
    response = client.get("/translations", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["items"] == []
