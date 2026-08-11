from tests.test_auth import VALID_PASSWORD, login, register

FAVORITE_PAYLOAD = {
    "source_lang": "en",
    "target_lang": "fr",
    "original_text": "hello",
    "translated_text": "bonjour",
}


def _auth_headers(client, email="favorites@example.com"):
    register(client, email=email, password=VALID_PASSWORD)
    tokens = login(client, email=email, password=VALID_PASSWORD).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_create_favorite_requires_auth(client):
    response = client.post("/favorites", json=FAVORITE_PAYLOAD)
    assert response.status_code in (401, 403)


def test_create_favorite_success(client):
    headers = _auth_headers(client)
    response = client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["source_lang"] == "en"
    assert body["translated_text"] == "bonjour"
    assert body["id"] is not None


def test_get_favorites_empty(client):
    headers = _auth_headers(client)
    response = client.get("/favorites", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"total": 0, "limit": 20, "offset": 0, "items": []}


def test_get_favorites_returns_created(client):
    headers = _auth_headers(client)
    client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers)
    response = client.get("/favorites", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["translated_text"] == "bonjour"


def test_get_favorites_pagination(client):
    headers = _auth_headers(client)
    for _ in range(3):
        client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers)

    response = client.get("/favorites?limit=2&offset=0", headers=headers)
    assert len(response.json()["items"]) == 2

    response = client.get("/favorites?limit=2&offset=2", headers=headers)
    assert len(response.json()["items"]) == 1


def test_get_favorites_only_returns_own(client):
    headers_a = _auth_headers(client, email="a@example.com")
    headers_b = _auth_headers(client, email="b@example.com")
    client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers_a)

    response = client.get("/favorites", headers=headers_b)
    assert response.json()["total"] == 0


def test_update_favorite_success(client):
    headers = _auth_headers(client)
    created = client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers).json()

    updated_payload = {**FAVORITE_PAYLOAD, "translated_text": "salut"}
    response = client.put(f"/favorites/{created['id']}", json=updated_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["translated_text"] == "salut"


def test_update_favorite_not_found(client):
    headers = _auth_headers(client)
    response = client.put("/favorites/999", json=FAVORITE_PAYLOAD, headers=headers)
    assert response.status_code == 404


def test_update_favorite_of_another_user_forbidden(client):
    headers_a = _auth_headers(client, email="a@example.com")
    headers_b = _auth_headers(client, email="b@example.com")
    created = client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers_a).json()

    response = client.put(f"/favorites/{created['id']}", json=FAVORITE_PAYLOAD, headers=headers_b)
    assert response.status_code == 404


def test_delete_favorite_success(client):
    headers = _auth_headers(client)
    created = client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers).json()

    response = client.delete(f"/favorites/{created['id']}", headers=headers)
    assert response.status_code == 200

    response = client.get("/favorites", headers=headers)
    assert response.json()["total"] == 0


def test_delete_favorite_not_found(client):
    headers = _auth_headers(client)
    response = client.delete("/favorites/999", headers=headers)
    assert response.status_code == 404


def test_delete_favorite_of_another_user_forbidden(client):
    headers_a = _auth_headers(client, email="a@example.com")
    headers_b = _auth_headers(client, email="b@example.com")
    created = client.post("/favorites", json=FAVORITE_PAYLOAD, headers=headers_a).json()

    response = client.delete(f"/favorites/{created['id']}", headers=headers_b)
    assert response.status_code == 404
