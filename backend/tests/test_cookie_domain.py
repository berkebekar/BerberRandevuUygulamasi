from starlette.requests import Request

import app.core.cookies as cookies


def _request_with_headers(headers: list[tuple[bytes, bytes]]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }
    return Request(scope)


def test_cookie_domain_dev_mode_matches_app_domain(monkeypatch):
    monkeypatch.setattr(
        cookies,
        "get_settings",
        lambda: type("S", (), {"env": "development", "app_domain": "example.com"})(),
    )
    request = _request_with_headers([(b"host", b"shop.example.com")])
    assert cookies.resolve_cookie_domain(request) == ".example.com"


def test_cookie_domain_production_matches_parent_domain(monkeypatch):
    monkeypatch.setattr(
        cookies,
        "get_settings",
        lambda: type("S", (), {"env": "production", "app_domain": "example.com"})(),
    )
    request = _request_with_headers([(b"host", b"shop.example.com")])
    assert cookies.resolve_cookie_domain(request) == ".example.com"


def test_cookie_domain_production_mismatch_falls_back_to_host_only(monkeypatch):
    monkeypatch.setattr(
        cookies,
        "get_settings",
        lambda: type("S", (), {"env": "production", "app_domain": "example.com"})(),
    )
    request = _request_with_headers([(b"host", b"random-host.invalid")])
    assert cookies.resolve_cookie_domain(request) is None


def test_cookie_domain_dev_localhost_subdomains_share_parent(monkeypatch):
    monkeypatch.setattr(
        cookies,
        "get_settings",
        lambda: type("S", (), {"env": "development", "app_domain": ""})(),
    )
    request = _request_with_headers([(b"host", b"api.berber.localhost:8000")])
    assert cookies.resolve_cookie_domain(request) == ".berber.localhost"
