"""Anubis proof-of-work challenge solver — A-Team omni-crawler addition.

Anubis (TecharoHQ/anubis, MIT (c) Xe Iaso / Techaro; full URL in NOTICE.md)
gates sites behind a SHA-256 proof-of-work: the client must find a nonce such that
sha256(challenge + nonce) has `difficulty` leading hex zeroes, then submit it to
the pass-challenge endpoint to receive a signed (ed25519 JWT) clearance cookie.

SAFETY / SCOPE (A-Team invariant — do not weaken):
  * Single client, ONE solve per host per run. No proxy rotation, no distributed
    solving, no multi-IP ban-evasion. (Enforced by caller: fetch_chain marks the
    host solved for the run.)
  * Difficulty is CAPPED (MAX_DIFFICULTY). Beyond the cap we refuse rather than
    burn CPU — solving an ever-harder PoW is an arms race that self-DoSes us and
    only exists to enable mass scraping.
  * This lets a legitimate single reader through a PoW wall on a public page. It
    is NOT a scraping engine. The abuse pattern it must never become is the one
    documented in the "creepy-crawlies" essay (millions of distributed requests
    solving PoW to strip-mine a git host; full citation in NOTICE.md).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Optional

# ── safety caps ──────────────────────────────────────────────────────────────
MAX_DIFFICULTY = 6            # hex-zero prefix length we are willing to solve
MAX_ITERATIONS = 1 << 27      # ~134M hashes hard ceiling (safety valve)

# ── detection ────────────────────────────────────────────────────────────────
# Markers unique to an Anubis interstitial. Kept narrow to avoid false positives
# on articles that merely mention Anubis.
ANUBIS_MARKERS: list[str] = [
    'id="anubis_version"',
    'id="anubis_challenge"',
    "/.within.website/x/cmd/anubis/",
    "im-a-bot-get-me-out-of-here",
    "anubis_challenge",
]

# Where the challenge JSON lives when embedded in the interstitial HTML.
_CHALLENGE_SCRIPT_RE = re.compile(
    r'<script[^>]*id="anubis_challenge"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
# Fallback: make-challenge API (older / JS-driven flow).
_MAKE_CHALLENGE_PATH = "/.within.website/x/cmd/anubis/api/make-challenge"
_PASS_CHALLENGE_PATH = "/.within.website/x/cmd/anubis/api/pass-challenge"


def looks_like_anubis(html: Optional[str], headers: Optional[dict] = None) -> bool:
    """Cheap structural check for an Anubis interstitial."""
    if html:
        low = html.lower()
        if any(m.lower() in low for m in ANUBIS_MARKERS):
            return True
    if headers:
        joined = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
        # Anubis emits X-Anubis-* response headers on the interstitial.
        if "x-anubis" in joined:
            return True
    return False


def solve_pow(challenge: str, difficulty: int, *,
              max_iterations: int = MAX_ITERATIONS) -> tuple[int, str]:
    """Return (nonce, hexdigest) where sha256(challenge+str(nonce)) has
    `difficulty` leading hex zeroes.

    Pure and deterministic — the unit-test anchor. Raises ValueError on a
    difficulty above the safety cap or on iteration exhaustion.
    """
    if not challenge:
        raise ValueError("empty challenge")
    if difficulty < 1:
        raise ValueError("difficulty must be >= 1")
    if difficulty > MAX_DIFFICULTY:
        raise ValueError(
            f"difficulty {difficulty} exceeds cap {MAX_DIFFICULTY} — refusing "
            f"(self-DoS / arms-race guard)"
        )
    target = "0" * difficulty
    nonce = 0
    while nonce < max_iterations:
        digest = hashlib.sha256(f"{challenge}{nonce}".encode()).hexdigest()
        if digest.startswith(target):
            return nonce, digest
        nonce += 1
    raise ValueError(f"PoW unsolved within {max_iterations} iterations")


def parse_challenge(html: str) -> Optional[dict]:
    """Extract {'data': str, 'difficulty': int, 'id': str|None} from an Anubis
    interstitial's embedded `<script id="anubis_challenge">` JSON.

    'data' is the string actually fed to the PoW hash. Returns None if no
    challenge is embedded (caller then tries the make-challenge API).

    Anubis (v1.2x) payload shape:
        {"rules":{"algorithm":"fast","difficulty":5},
         "challenge":{"randomData":"<hex>","id":"<uuid>","difficulty":5,...}}
    Older Anubis used a bare string challenge — handled for back-compat.
    """
    if not html:
        return None
    m = _CHALLENGE_SCRIPT_RE.search(html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        return None
    return _normalize_challenge(data)


def _normalize_challenge(data: dict) -> Optional[dict]:
    """Coerce Anubis challenge payload variants into {data, difficulty, id}.

    The PoW is sha256(randomData + nonce) with `difficulty` leading hex zeroes
    (confirmed against live v1.26/v1.27 main.mjs: worker hashes `challenge.randomData`,
    threshold = 16**-difficulty).
    """
    if not isinstance(data, dict):
        return None
    rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
    challenge = data.get("challenge")

    pow_data = None
    cid = None
    difficulty = data.get("difficulty", rules.get("difficulty"))

    if isinstance(challenge, dict):
        pow_data = challenge.get("randomData") or challenge.get("challenge")
        cid = challenge.get("id")
        if difficulty is None:
            difficulty = challenge.get("difficulty")
    elif isinstance(challenge, str):
        pow_data = challenge  # legacy bare-string challenge
        cid = data.get("id")

    if not pow_data or difficulty is None:
        return None
    try:
        difficulty = int(difficulty)
    except (TypeError, ValueError):
        return None
    return {"data": str(pow_data), "difficulty": difficulty, "id": cid}


def solve_from_session(session, base_url: str, html: str, *,
                       timeout: int = 25, logger=None) -> bool:
    """Full flow against a live Anubis wall using a cookie-persistent session
    (curl_cffi Session or compatible: .get(url, timeout=...) -> resp with
    .status_code/.text and cookie jar).

    Returns True if a clearance cookie was obtained (stored on the session by
    the pass-challenge Set-Cookie), else False. Endpoint/cookie specifics are
    intentionally discovered from the page + standard Anubis paths and verified
    live — see module docstring for the safety contract.
    """
    def _log(msg):
        if logger:
            logger(f"[anubis] {msg}")

    from urllib.parse import urlparse, urlencode
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # 1. Obtain the challenge — embedded JSON first, then make-challenge API.
    ch = parse_challenge(html)
    if ch is None:
        try:
            resp = session.get(origin + _MAKE_CHALLENGE_PATH, timeout=timeout)
            if getattr(resp, "status_code", 0) == 200:
                ch = _normalize_challenge(json.loads(resp.text))
        except Exception as e:  # noqa: BLE001 — network/parse best-effort
            _log(f"make-challenge failed: {e}")
    if ch is None:
        _log("no challenge found")
        return False

    # 2. Solve (capped): sha256(randomData + nonce), `difficulty` leading hex zeroes.
    try:
        started = time.monotonic()
        nonce, digest = solve_pow(ch["data"], ch["difficulty"])
        elapsed_ms = int((time.monotonic() - started) * 1000)
    except ValueError as e:
        _log(f"refused/failed: {e}")
        return False
    _log(f"solved difficulty={ch['difficulty']} nonce={nonce} in {elapsed_ms}ms")

    # 3. Submit → server Set-Cookies the JWT on the same session; the caller
    #    then re-fetches (warm session now carries clearance). GET with
    #    querystring incl. the challenge id (matches main.mjs pass-challenge).
    submit = {"response": digest, "nonce": nonce,
              "redir": base_url, "elapsedTime": elapsed_ms}
    if ch.get("id"):
        submit["id"] = ch["id"]
    params = urlencode(submit)
    try:
        resp = session.get(f"{origin}{_PASS_CHALLENGE_PATH}?{params}",
                           timeout=timeout)
    except Exception as e:  # noqa: BLE001
        _log(f"pass-challenge failed: {e}")
        return False

    # Success = the session now holds an anubis auth cookie.
    try:
        cookie_names = " ".join(getattr(session, "cookies", {}).keys()).lower()
    except Exception:  # noqa: BLE001
        cookie_names = ""
    ok = "anubis" in cookie_names or getattr(resp, "status_code", 0) in (200, 302)
    _log("cleared" if ok else "no clearance cookie")
    return ok
