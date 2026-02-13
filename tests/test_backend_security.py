from Couches.Backend.app import _hash_password, _verify_password


def test_password_hash_and_verify():
    password = "very-secure-password"
    encoded = _hash_password(password)
    assert encoded.startswith("pbkdf2_sha256$")
    assert _verify_password(password, encoded)
    assert not _verify_password("wrong-password", encoded)
