from product_requirement_loop.web.auth_passwords import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    stored = hash_password("correct-horse")
    assert stored.startswith("pbkdf2_sha256$120000$")
    assert verify_password("correct-horse", stored)
    assert not verify_password("wrong-password", stored)


def test_hash_uses_unique_salt():
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
    assert verify_password("same", a)
    assert verify_password("same", b)


def test_verify_rejects_malformed_or_unknown_algo():
    assert not verify_password("x", "not-a-hash")
    assert not verify_password("x", "md5$1$dead$beef")
    assert not verify_password("x", "pbkdf2_sha256$bad$zz$yy")
