"""Deterministic tests for the robots.txt politeness gate (A-Team)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import robots  # noqa: E402

_DISALLOW_ALL = ["User-agent: *", "Disallow: /"]
_DISALLOW_PRIVATE = ["User-agent: *", "Disallow: /private/"]


def _stub_fetch(lines):
    """Return a _fetch_robots replacement yielding fixed robots.txt lines."""
    return lambda robots_url, timeout: lines


def setup_function(_):
    robots.reset_cache()


def test_disallow_all_refuses(monkeypatch=None):
    robots._fetch_robots = _stub_fetch(_DISALLOW_ALL)
    robots.reset_cache()
    allowed, why = robots.is_allowed("https://example.com/anything", ignore=False)
    assert allowed is False
    assert why.startswith("robots:disallow")


def test_path_scoped_disallow():
    robots._fetch_robots = _stub_fetch(_DISALLOW_PRIVATE)
    robots.reset_cache()
    assert robots.is_allowed("https://example.com/private/x", ignore=False)[0] is False
    robots.reset_cache()
    assert robots.is_allowed("https://example.com/public/x", ignore=False)[0] is True


def test_opt_out_overrides_disallow():
    robots._fetch_robots = _stub_fetch(_DISALLOW_ALL)
    robots.reset_cache()
    allowed, why = robots.is_allowed("https://example.com/x", ignore=True)
    assert allowed is True
    assert "opt-out" in why


def test_missing_robots_allows():
    # _fetch_robots returns None on 4xx/404/network error → allow-all (RFC 9309).
    robots._fetch_robots = lambda robots_url, timeout: None
    robots.reset_cache()
    allowed, why = robots.is_allowed("https://example.com/x", ignore=False)
    assert allowed is True
    assert "unavailable" in why


def test_env_opt_out(monkeypatch=None):
    robots._fetch_robots = _stub_fetch(_DISALLOW_ALL)
    robots.reset_cache()
    os.environ["INSANE_IGNORE_ROBOTS"] = "1"
    try:
        assert robots.is_allowed("https://example.com/x")[0] is True
    finally:
        del os.environ["INSANE_IGNORE_ROBOTS"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            robots.reset_cache()
            fn()
            print(f"PASS {name}")
    print("all robots tests passed")
