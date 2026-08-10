from unittest.mock import patch

from deep_translator.exceptions import NotValidPayload, ServerException, TooManyRequests

from tests.test_auth import VALID_PASSWORD, login, register

AUTH_HEADER_EMAIL = "translator@example.com"


def _auth_headers(client):
    register(client, email=AUTH_HEADER_EMAIL, password=VALID_PASSWORD)
    tokens = login(client, email=AUTH_HEADER_EMAIL, password=VALID_PASSWORD).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _translate_request(client, headers, target_langs=None, text="hello", source_lang="en"):
    return client.post(
        "/translate",
        json={"text": text, "source_lang": source_lang, "target_langs": target_langs or ["fr"]},
        headers=headers,
    )


def test_translate_requires_auth(client):
    response = _translate_request(client, headers={})
    assert response.status_code in (401, 403)


def test_translate_success(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.return_value = "bonjour"
        response = _translate_request(client, headers, target_langs=["fr"])

    assert response.status_code == 200
    body = response.json()
    assert body["translations"] == {"fr": "bonjour"}
    assert body["source_lang"] == "en"
    assert body["original_text"] == "hello"


def test_translate_multiple_targets(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.side_effect = ["bonjour", "hola"]
        response = _translate_request(client, headers, target_langs=["fr", "es"])

    assert response.status_code == 200
    assert response.json()["translations"] == {"fr": "bonjour", "es": "hola"}


def test_translate_invalid_payload_returns_400(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.side_effect = NotValidPayload("bad payload")
        response = _translate_request(client, headers, target_langs=["fr"])

    assert response.status_code == 400


def test_translate_provider_rate_limit_returns_429(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.side_effect = TooManyRequests()
        response = _translate_request(client, headers, target_langs=["fr"])

    assert response.status_code == 429


def test_translate_provider_error_returns_502(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.side_effect = ServerException(500)
        response = _translate_request(client, headers, target_langs=["fr"])

    assert response.status_code == 502


def test_translate_persists_history(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.return_value = "bonjour"
        _translate_request(client, headers, target_langs=["fr"])

    history = client.get("/translations", headers=headers)
    assert history.status_code == 200
    body = history.json()
    assert body["total"] == 1
    assert body["items"][0]["translated_text"] == "bonjour"


def test_translations_requires_auth(client):
    response = client.get("/translations")
    assert response.status_code in (401, 403)


def test_translations_pagination(client):
    headers = _auth_headers(client)
    with patch("routers.translate.GoogleTranslator") as mock_translator:
        mock_translator.return_value.translate.return_value = "bonjour"
        for _ in range(3):
            _translate_request(client, headers, target_langs=["fr"])

    response = client.get("/translations?limit=2&offset=0", headers=headers)
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    response = client.get("/translations?limit=2&offset=2", headers=headers)
    body = response.json()
    assert len(body["items"]) == 1
