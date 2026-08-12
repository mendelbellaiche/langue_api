from unittest.mock import patch

import models
from security import create_password_reset_token
from tests.test_auth import VALID_PASSWORD, login, register

EMAIL = "reset@example.com"
NEW_PASSWORD = "NewStrongP@ss1"


def _get_user(db_session, email=EMAIL):
    return db_session.query(models.User).filter_by(email=email).first()


def test_request_reset_unknown_email_returns_generic_message(client):
    response = client.post("/password-reset/request", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert "message" in response.json()


def test_request_reset_known_email_sends_email(client):
    register(client, email=EMAIL)
    with patch("routers.auth.send_password_reset_email") as mock_send:
        response = client.post("/password-reset/request", json={"email": EMAIL})

    assert response.status_code == 200
    assert "message" in response.json()
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == EMAIL


def test_request_reset_email_failure_still_returns_generic_message(client):
    register(client, email=EMAIL)
    with patch("routers.auth.send_password_reset_email", side_effect=Exception("smtp down")):
        response = client.post("/password-reset/request", json={"email": EMAIL})

    assert response.status_code == 200
    assert "message" in response.json()


def test_confirm_reset_with_invalid_token_rejected(client):
    response = client.post(
        "/password-reset/confirm", json={"token": "not-a-real-token", "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 400


def test_confirm_reset_weak_password_rejected(client, db_session):
    register(client, email=EMAIL)
    token = create_password_reset_token(_get_user(db_session), db_session)

    response = client.post("/password-reset/confirm", json={"token": token, "new_password": "weak"})
    assert response.status_code == 422


def test_confirm_reset_success_allows_login_with_new_password(client, db_session):
    register(client, email=EMAIL)
    token = create_password_reset_token(_get_user(db_session), db_session)

    response = client.post("/password-reset/confirm", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 200

    old_login = login(client, email=EMAIL, password=VALID_PASSWORD)
    assert old_login.status_code == 401

    new_login = login(client, email=EMAIL, password=NEW_PASSWORD)
    assert new_login.status_code == 200


def test_confirm_reset_token_cannot_be_reused(client, db_session):
    register(client, email=EMAIL)
    token = create_password_reset_token(_get_user(db_session), db_session)

    client.post("/password-reset/confirm", json={"token": token, "new_password": NEW_PASSWORD})
    reuse_response = client.post(
        "/password-reset/confirm", json={"token": token, "new_password": "AnotherP@ss1"}
    )
    assert reuse_response.status_code == 400


def test_confirm_reset_revokes_existing_refresh_tokens(client, db_session):
    register(client, email=EMAIL)
    tokens = login(client, email=EMAIL, password=VALID_PASSWORD).json()

    reset_token = create_password_reset_token(_get_user(db_session), db_session)
    client.post("/password-reset/confirm", json={"token": reset_token, "new_password": NEW_PASSWORD})

    refresh_response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 401


def test_request_password_reset_is_rate_limited(client):
    register(client, email=EMAIL)
    with patch("routers.auth.send_password_reset_email"):
        for _ in range(5):
            client.post("/password-reset/request", json={"email": EMAIL})
        response = client.post("/password-reset/request", json={"email": EMAIL})
    assert response.status_code == 429
