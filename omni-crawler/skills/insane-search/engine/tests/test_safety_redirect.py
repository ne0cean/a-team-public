"""Regression tests for safety.safe_get — SSRF-safe manual redirect following.

Covers the HIGH finding from the 2026-09-12 omni-crawler review: curl_cffi
follows redirects by default, so classifying only the original URL let a
302 → 169.254.169.254 (or loopback) through. safe_get re-classifies every hop.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import safety  # noqa: E402


class _Resp:
    def __init__(self, status, location=None, content=b"OK", text="OK"):
        self.status_code = status
        self.headers = {"Location": location} if location else {}
        self.content = content
        self.text = text


def _chain(*responses):
    """Return a _get callable that yields the given responses in order and
    records the URLs it was asked to fetch."""
    seq = list(responses)
    calls = []

    def _get(u):
        calls.append(u)
        return seq.pop(0)

    _get.calls = calls
    return _get


def test_redirect_to_metadata_blocked():
    # Safe original → 302 → cloud metadata. Second hop must be refused BEFORE fetch.
    getter = _chain(
        _Resp(302, location="http://169.254.169.254/latest/meta-data/"),
        _Resp(200, content=b"SECRET"),   # must never be reached
    )
    r = safety.safe_get("https://trusted.example.com/image.png", _get=getter)
    assert r is None
    assert getter.calls == ["https://trusted.example.com/image.png"]  # stopped after hop 1


def test_redirect_to_loopback_blocked():
    getter = _chain(_Resp(301, location="http://127.0.0.1:8080/admin"))
    r = safety.safe_get("https://trusted.example.com/x", _get=getter)
    assert r is None


def test_safe_redirect_followed():
    getter = _chain(
        _Resp(302, location="https://cdn.example.com/real.png"),
        _Resp(200, content=b"IMGBYTES"),
    )
    r = safety.safe_get("https://example.com/a.png", allow_private=False, _get=getter)
    assert r is not None and r.status_code == 200 and r.content == b"IMGBYTES"
    assert getter.calls[-1] == "https://cdn.example.com/real.png"


def test_original_unsafe_never_fetched():
    getter = _chain(_Resp(200))
    r = safety.safe_get("http://169.254.169.254/latest/meta-data/", _get=getter)
    assert r is None
    assert getter.calls == []   # classified unsafe before any fetch


def test_redirect_loop_capped():
    # Endless redirect to a *safe* host → capped at max_redirects, returns None.
    def _get(u):
        return _Resp(302, location="https://example.com/again")
    r = safety.safe_get("https://example.com/start", max_redirects=3, _get=_get)
    assert r is None


def test_no_location_hands_back_response():
    getter = _chain(_Resp(302, location=None))
    r = safety.safe_get("https://example.com/x", _get=getter)
    assert r is not None and r.status_code == 302


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all safety_redirect tests passed")
