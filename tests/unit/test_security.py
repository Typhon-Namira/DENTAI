import uuid

import pytest

from app.auth.security import decode_token, hash_password, make_access_token, verify_password
from app.core.errors import AppError


def test_password_hash_is_not_plaintext():
    hashed = hash_password("Correct-Horse-Battery-47")
    assert hashed != "Correct-Horse-Battery-47"
    assert verify_password("Correct-Horse-Battery-47", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_is_bound_to_server_clinic_context():
    clinic = uuid.uuid4()
    token = make_access_token(uuid.uuid4(), clinic, 3)
    payload = decode_token(token, "access")
    assert payload["clinic"] == str(clinic)
    assert payload["ver"] == 3


def test_access_token_cannot_be_used_as_refresh():
    with pytest.raises(AppError):
        decode_token(make_access_token(uuid.uuid4(), uuid.uuid4(), 1), "refresh")
