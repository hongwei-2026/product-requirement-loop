import pytest

from product_requirement_loop.web import security_guard as sg


@pytest.fixture(autouse=True)
def _reset_attempts():
    with sg._lock:
        sg._attempts.clear()
    yield
    with sg._lock:
        sg._attempts.clear()


def test_allow_auth_attempt_under_limit():
    key = "10.0.0.1"
    for _ in range(sg.MAX_ATTEMPTS):
        assert sg.allow_auth_attempt(key) is True
    assert sg.allow_auth_attempt(key) is False


def test_allow_auth_attempt_is_per_key():
    assert sg.allow_auth_attempt("a") is True
    for _ in range(sg.MAX_ATTEMPTS):
        sg.allow_auth_attempt("b")
    assert sg.allow_auth_attempt("b") is False
    assert sg.allow_auth_attempt("a") is True


def test_resolve_bind_host_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("BIND_HOST", raising=False)
    monkeypatch.delenv("SECURITY_ALLOW_LAN", raising=False)
    assert sg.resolve_bind_host() == "127.0.0.1"


def test_resolve_bind_host_rejects_all_interfaces_without_lan(monkeypatch):
    monkeypatch.setenv("BIND_HOST", "0.0.0.0")
    monkeypatch.delenv("SECURITY_ALLOW_LAN", raising=False)
    with pytest.raises(RuntimeError, match="拒绝绑定"):
        sg.resolve_bind_host()


def test_resolve_bind_host_allows_lan_when_flag_set(monkeypatch):
    monkeypatch.setenv("BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("SECURITY_ALLOW_LAN", "1")
    assert sg.resolve_bind_host() == "0.0.0.0"


def test_registration_allowed_flag(monkeypatch):
    monkeypatch.delenv("SECURITY_DISABLE_REGISTER", raising=False)
    assert sg.registration_allowed() is True
    monkeypatch.setenv("SECURITY_DISABLE_REGISTER", "1")
    assert sg.registration_allowed() is False


def test_security_headers_include_nosniff_and_frame_deny():
    headers = dict(sg.security_headers())
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
