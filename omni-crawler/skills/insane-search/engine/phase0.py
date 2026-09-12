"""Phase 0 — official public-API router (the SANCTIONED exception to No-Site-Name).

Per SKILL.md R5, platforms that publish official no-auth public endpoints get a
deterministic route tried BEFORE the generic WAF grid. This is the *enforced,
in-engine* version of what used to be agent-driven curl snippets in SKILL.md —
so the agent can no longer silently skip it (which is exactly how Reddit/X were
wrongly declared "blocked": the grid 403'd on `.json` and nobody tried `.rss`).

This file is the ONLY engine/ module allowed to name platform hosts; it is
exempted in `bias_check.EXPLICIT_ALLOW_FILES`. Do NOT add per-site logic to any
other engine file — generic WAF handling stays site-agnostic.

Contract:
    route(url) -> Optional[dict]
      None              → url is not a recognised Phase-0 platform; caller runs
                          the generic grid as usual.
      {"platform","ok","route","content","final_url","attempts":[...]}
                        → recognised platform. `ok` says whether an official
                          route succeeded. Even on ok=False the caller should
                          fall through to the grid, but `attempts` is recorded
                          so failure is never silent.

Each attempt dict: {"route","platform","ok","status","bytes","note"}.
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional
from urllib.parse import urlsplit

from . import platform_bridge
from . import video


# --- low-level helpers -------------------------------------------------------
def _cffi_get(url: str, *, impersonate: str = "safari", timeout: int = 15):
    from curl_cffi import requests as r  # lazy: engine works even if missing
    return r.get(
        url,
        impersonate=impersonate,  # type: ignore[arg-type]
        timeout=timeout,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        },
        allow_redirects=True,
    )


def _host(url: str) -> str:
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h  # strip the literal "www." prefix only


def _attempt(platform: str, route: str, ok: bool, status: int, body: str, note: str = "") -> dict:
    return {"platform": platform, "route": route, "ok": ok, "status": status,
            "bytes": len(body or ""), "note": note}


# --- platform detectors ------------------------------------------------------
def _detect(url: str) -> Optional[str]:
    h = _host(url)
    if not h:
        return None
    if "reddit.com" in h or h == "redd.it":
        return "reddit"
    if h in ("x.com", "twitter.com") or h.endswith(".x.com") or h.endswith(".twitter.com"):
        return "x"
    if "youtube.com" in h or h == "youtu.be":
        return "youtube"
    if h == "github.com" or h == "gist.github.com":
        return "github"
    return None


# --- reddit ------------------------------------------------------------------
def _reddit(url: str, timeout: int) -> dict:
    attempts: list[dict] = []
    base = url.split("?", 1)[0].rstrip("/")
    # Build an .rss / .json target from the path (works for /r/<sub> and post URLs).
    rss_url = base + ("/.rss" if "/comments/" not in base else ".rss")
    json_url = base + ("/.json" if "/comments/" not in base else ".json")

    # Route 1: RSS (the route that actually survives — Reddit gates the JSON API).
    try:
        x = _cffi_get(rss_url, timeout=timeout)
        ok = x.status_code == 200 and ("<rss" in x.text or "<feed" in x.text)
        attempts.append(_attempt("reddit", "rss", ok, x.status_code, x.text,
                                 "feed" if ok else "no-feed-markers"))
        if ok:
            return {"platform": "reddit", "ok": True, "route": "rss",
                    "content": x.text, "final_url": rss_url, "attempts": attempts}
    except Exception as e:
        attempts.append(_attempt("reddit", "rss", False, 0, "", f"{type(e).__name__}"))

    # Route 2: JSON via curl_cffi (often 403 now, but try — cheap).
    try:
        x = _cffi_get(json_url, timeout=timeout)
        ok = x.status_code == 200 and x.text.lstrip().startswith(("{", "["))
        attempts.append(_attempt("reddit", "json", ok, x.status_code, x.text,
                                 "json" if ok else f"status={x.status_code}"))
        if ok:
            return {"platform": "reddit", "ok": True, "route": "json",
                    "content": x.text, "final_url": json_url, "attempts": attempts}
    except Exception as e:
        attempts.append(_attempt("reddit", "json", False, 0, "", f"{type(e).__name__}"))

    return {"platform": "reddit", "ok": False, "route": None, "content": "",
            "final_url": url, "attempts": attempts}


# --- x / twitter -------------------------------------------------------------
_TWEET_ID_RE = re.compile(r"/status(?:es)?/(\d+)")


def _x(url: str, timeout: int) -> dict:
    attempts: list[dict] = []
    m = _TWEET_ID_RE.search(url)

    if m:  # single tweet → tweet-result + oembed (both no-auth, reliable)
        tid = m.group(1)
        try:
            x = _cffi_get(f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&token=a", timeout=timeout)
            d = x.json() if x.status_code == 200 else {}
            ok = bool(d.get("text"))
            attempts.append(_attempt("x", "tweet-result", ok, x.status_code, x.text,
                                     "has-text" if ok else f"status={x.status_code}"))
            if ok:
                return {"platform": "x", "ok": True, "route": "tweet-result",
                        "content": x.text, "final_url": url, "attempts": attempts}
        except Exception as e:
            attempts.append(_attempt("x", "tweet-result", False, 0, "", f"{type(e).__name__}"))
        try:
            ourl = f"https://publish.twitter.com/oembed?url=https://twitter.com/i/status/{tid}&omit_script=1"
            x = _cffi_get(ourl, timeout=timeout)
            d = x.json() if x.status_code == 200 else {}
            ok = bool(d.get("html"))
            attempts.append(_attempt("x", "oembed", ok, x.status_code, x.text,
                                     "has-html" if ok else f"status={x.status_code}"))
            if ok:
                return {"platform": "x", "ok": True, "route": "oembed",
                        "content": x.text, "final_url": ourl, "attempts": attempts}
        except Exception as e:
            attempts.append(_attempt("x", "oembed", False, 0, "", f"{type(e).__name__}"))
    else:  # profile timeline → syndication (rate-limit-prone; retry once)
        handle = urlsplit(url).path.strip("/").split("/")[0]
        _reserved = {"i", "search", "home", "explore", "messages", "notifications", "settings", "hashtag"}
        if handle and handle.lower() not in _reserved:
            surl = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
            for attempt_no in range(2):
                try:
                    x = _cffi_get(surl, timeout=timeout)
                    ok = x.status_code == 200 and "__NEXT_DATA__" in x.text
                    attempts.append(_attempt("x", f"syndication-timeline#{attempt_no+1}", ok,
                                             x.status_code, x.text,
                                             "timeline" if ok else f"status={x.status_code}"))
                    if ok:
                        return {"platform": "x", "ok": True, "route": "syndication-timeline",
                                "content": x.text, "final_url": surl, "attempts": attempts}
                except Exception as e:
                    attempts.append(_attempt("x", f"syndication-timeline#{attempt_no+1}", False, 0, "", f"{type(e).__name__}"))

    return {"platform": "x", "ok": False, "route": None, "content": "",
            "final_url": url, "attempts": attempts}


# --- youtube -----------------------------------------------------------------
def _youtube(url: str, timeout: int) -> dict:
    attempts: list[dict] = []
    try:
        p = subprocess.run(
            ["yt-dlp", "--dump-json", "--skip-download", url],
            capture_output=True, text=True, timeout=max(timeout, 60),
        )
        ok = p.returncode == 0 and p.stdout.strip().startswith("{")
        note = "json" if ok else (p.stderr or "").strip()[:80]
        attempts.append(_attempt("youtube", "yt-dlp", ok, 200 if ok else 0, p.stdout, note))
        if ok:
            content = p.stdout
            # Phase E: opt-in transcript enrichment (INSANE_TRANSCRIPT=1). Public
            # captions only; appends a "## Transcript" section. Default off →
            # existing metadata-only behaviour unchanged.
            if video.transcript_enabled():
                content = video.maybe_append_transcript(content, p.stdout, timeout=timeout)
            return {"platform": "youtube", "ok": True, "route": "yt-dlp",
                    "content": content, "final_url": url, "attempts": attempts}
    except FileNotFoundError:
        attempts.append(_attempt("youtube", "yt-dlp", False, 0, "", "yt-dlp not installed"))
    except Exception as e:
        attempts.append(_attempt("youtube", "yt-dlp", False, 0, "", f"{type(e).__name__}"))
    return {"platform": "youtube", "ok": False, "route": None, "content": "",
            "final_url": url, "attempts": attempts}


# --- github (agent-reach bridge via gh CLI) ----------------------------------
# git-clone-first (Phase -1) already handles bare repos → repo card. This router
# covers the surfaces a clone CANNOT: issues, PRs, and gists — the "read the
# discussion, not the tree" gap. Delegates the actual `gh` call to
# platform_bridge (mechanism), keeping URL parsing here (host-naming file).
_GH_ISSUE_RE = re.compile(r"^/([^/]+)/([^/]+)/issues/(\d+)")
_GH_PR_RE = re.compile(r"^/([^/]+)/([^/]+)/pull/(\d+)")


def _github(url: str, timeout: int) -> dict:
    attempts: list[dict] = []
    parts = urlsplit(url)
    path = parts.path
    host = _host(url)
    to = max(timeout, 30)

    def _done(route: str, ok: bool, out: str, note: str) -> Optional[dict]:
        attempts.append(_attempt("github", route, ok, 200 if ok else 0, out, note))
        if ok:
            return {"platform": "github", "ok": True, "route": route,
                    "content": out, "final_url": url, "attempts": attempts}
        return None

    # gist.github.com/<user>/<id>  or  gist.github.com/<id>
    if host == "gist.github.com":
        gid = [seg for seg in path.split("/") if seg]
        if gid:
            ok, out, note = platform_bridge.run("gh", ["gist", "view", "--", gid[-1]], to)
            r = _done("gh-gist", ok, out, note)
            if r:
                return r
        return {"platform": "github", "ok": False, "route": None, "content": "",
                "final_url": url, "attempts": attempts}

    m = _GH_ISSUE_RE.match(path)
    if m:
        repo = f"{m.group(1)}/{m.group(2)}"
        ok, out, note = platform_bridge.run(
            "gh", ["issue", "view", m.group(3), "--repo", repo, "--comments"], to)
        r = _done("gh-issue", ok, out, note)
        if r:
            return r
        return {"platform": "github", "ok": False, "route": None, "content": "",
                "final_url": url, "attempts": attempts}

    m = _GH_PR_RE.match(path)
    if m:
        repo = f"{m.group(1)}/{m.group(2)}"
        ok, out, note = platform_bridge.run(
            "gh", ["pr", "view", m.group(3), "--repo", repo, "--comments"], to)
        r = _done("gh-pr", ok, out, note)
        if r:
            return r
        return {"platform": "github", "ok": False, "route": None, "content": "",
                "final_url": url, "attempts": attempts}

    # Bare repo / tree / blob / other → not our gap; let git-clone / grid handle.
    return {"platform": "github", "ok": False, "route": None, "content": "",
            "final_url": url, "attempts": attempts}


_ROUTERS = {"reddit": _reddit, "x": _x, "youtube": _youtube, "github": _github}


# --- public entrypoint -------------------------------------------------------
def route(url: str, *, timeout: int = 15) -> Optional[dict]:
    platform = _detect(url)
    if platform is None:
        return None
    return _ROUTERS[platform](url, timeout)
