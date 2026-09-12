"""robots.txt politeness gate — A-Team omni-crawler addition.

The upstream insane-search engine has no robots.txt handling: it treats every
URL as fair game. That is exactly the "rude crawler" behaviour condemned in the
"creepy-crawlies" essay that motivated this feature. This module is the minimal
politeness layer: before the *generic HTML grid* scrapes a page, check the
site's robots.txt and refuse Disallowed paths by default.

SCOPE / SAFETY (A-Team invariant):
  * Gates only the generic diversity grid (Phase 1+). Sanctioned paths the
    article endorses — git-clone-first (Phase -1) and official public APIs
    (Phase 0) — are NOT gated here; they are the server-friendly routes.
  * Default is COMPLY. Override only with an explicit opt-out
    (INSANE_IGNORE_ROBOTS=1 or ignore=True) — e.g. a maintainer crawling their
    own site. Opt-out is logged by the caller, never silent.
  * Fail-OPEN on robots.txt fetch/parse errors and on 4xx/404 (RFC 9309:
    "unavailable for access" → allowed). We only ever *refuse* on an explicit
    Disallow match, so a flaky robots endpoint can't wedge the whole chain.
  * The robots URL itself is SSRF-classified (engine.safety); an unsafe robots
    host is skipped (the later fetch guard blocks the real request anyway).
"""
from __future__ import annotations

import os
import urllib.robotparser
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from . import safety

# Identifiable token so a site owner can target us in robots.txt if they wish.
DEFAULT_UA = "omni-crawler"

# Per-host parser cache for one run: {host: RobotFileParser | None}.
# None = robots.txt was unreadable/absent → treat as allow-all.
_CACHE: dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}


def ignore_default() -> bool:
    return os.environ.get("INSANE_IGNORE_ROBOTS", "") in ("1", "true", "yes")


def _robots_url(url: str) -> Optional[str]:
    try:
        p = urlsplit(url)
    except Exception:
        return None
    if p.scheme not in ("http", "https") or not p.hostname:
        return None
    return urlunsplit((p.scheme, p.netloc, "/robots.txt", "", ""))


def _fetch_robots(robots_url: str, timeout: int) -> Optional[list[str]]:
    """Return robots.txt lines, or None on any error / non-2xx (→ allow-all).

    Uses safety.safe_get (curl_cffi under the hood) so redirects are followed
    manually with per-hop SSRF re-classification. No stdlib urllib fallback:
    urllib.urlopen follows redirects unchecked, which would reintroduce the SSRF
    hole this gate exists to close.
    """
    try:
        # safe_get follows redirects manually, re-classifying each hop — a
        # robots.txt that 302s to an internal 200 can't smuggle an allow-all.
        r = safety.safe_get(robots_url, impersonate="safari", timeout=timeout)
        if r is None:
            return None            # unsafe hop / curl missing / network error
        if r.status_code >= 400:
            return None            # 4xx/5xx → unavailable → allow-all
        return (r.text or "").splitlines()
    except Exception:
        return None


def _parser_for(url: str, timeout: int) -> Optional[urllib.robotparser.RobotFileParser]:
    host = urlsplit(url).netloc
    if host in _CACHE:
        return _CACHE[host]
    robots_url = _robots_url(url)
    parser: Optional[urllib.robotparser.RobotFileParser] = None
    if robots_url:
        safe, _reason = safety.classify_url(robots_url,
                                            allow_private=safety.allow_private_default())
        if safe:
            lines = _fetch_robots(robots_url, timeout)
            if lines is not None:
                parser = urllib.robotparser.RobotFileParser()
                try:
                    parser.parse(lines)
                except Exception:
                    parser = None
    _CACHE[host] = parser
    return parser


def is_allowed(
    url: str,
    *,
    user_agent: str = DEFAULT_UA,
    timeout: int = 10,
    ignore: Optional[bool] = None,
) -> tuple[bool, str]:
    """(allowed, reason). Refuses ONLY on an explicit robots Disallow match;
    every other outcome (opt-out, no robots.txt, fetch/parse error, safety
    skip) is allow-with-reason so the fetch chain is never wedged."""
    if ignore is None:
        ignore = ignore_default()
    if ignore:
        return True, "robots:ignored(opt-out)"

    parser = _parser_for(url, timeout)
    if parser is None:
        return True, "robots:unavailable(allow)"
    try:
        if parser.can_fetch(user_agent, url):
            return True, "robots:allowed"
        return False, f"robots:disallow:{urlsplit(url).path or '/'}"
    except Exception:
        return True, "robots:parse_error(allow)"


def reset_cache() -> None:
    """Clear the per-run host cache (tests / long-lived processes)."""
    _CACHE.clear()
