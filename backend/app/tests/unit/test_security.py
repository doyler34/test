import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_jwt,
    decode_jwt,
    hash_password,
    hash_token,
    new_api_key,
    new_refresh_token,
    verify_password,
)


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_jwt_round_trip() -> None:
    user_id = uuid.uuid4()
    token = create_jwt(subject=user_id, token_type="access", expires_delta=timedelta(minutes=5))
    payload = decode_jwt(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_expired_jwt_is_rejected() -> None:
    user_id = uuid.uuid4()
    token = create_jwt(subject=user_id, token_type="access", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_jwt(token)


def test_refresh_token_only_hash_is_derivable_from_raw() -> None:
    raw, token_hash, expires_at = new_refresh_token()
    assert token_hash == hash_token(raw)
    assert token_hash != raw
    assert expires_at is not None


def test_api_key_prefix_and_hash() -> None:
    raw, prefix, key_hash = new_api_key()
    assert raw.startswith(prefix)
    assert key_hash == hash_token(raw)
    assert key_hash != raw
