def test_password_hash():
    from app.core.security import get_password_hash, verify_password
    password = "testpass123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_access_token():
    from app.core.security import create_access_token, decode_access_token
    data = {"sub": "user123", "email": "test@example.com", "role": "doctor"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user123"
    assert decoded["email"] == "test@example.com"
