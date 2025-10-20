"""Tests for security helpers."""

import pytest

from app.core import security


def test_password_hash_roundtrip():
    password = "StrongPassw0rd!"
    hashed = security.get_password_hash(password)

    assert hashed != password
    assert security.verify_password(password, hashed)
    assert not security.verify_password("wrongpassword", hashed)


def test_access_token_contains_expected_claims():
    token = security.create_access_token("user-123", {"email": "user@example.com"})
    payload = security.decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["email"] == "user@example.com"
    assert "exp" in payload


def test_refresh_token_decodes_correctly():
    token = security.create_refresh_token("user-456")
    payload = security.decode_refresh_token(token)

    assert payload["sub"] == "user-456"


def test_decode_access_token_with_invalid_value_raises():
    with pytest.raises(ValueError):
        security.decode_access_token("not-a-real-token")

