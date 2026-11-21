"""OCR enrichment — A-Team omni-crawler addition (web-crawler-ocr port).

After a successful fetch, if the content references images AND a Gemini key is
present AND OCR is opted in, download each image, OCR it via the Gemini REST
API, and inline the extracted text under its markdown reference (or append a
section when there is no reference to anchor to). Ported from the web-crawler-ocr
skill's extract-images + insert_ocr_inline logic.

SCOPE / SAFETY:
  * OPT-IN only (enable_ocr=True or INSANE_OCR=1) — OCR spends API quota and
    downloads bytes, so it never runs implicitly. Absent the opt-in OR the key
    OR any images, it is a no-op that returns the content unchanged.
  * Every image URL is SSRF-classified (engine.safety) before download; private/
    loopback/metadata targets are skipped.
  * Image count is capped (max_images) — bounded work, no scrape amplification.
  * Enrichment never raises into the fetch chain: callers wrap defensively and
    a failed image is recorded in the trace, not fatal.
"""
from __future__ import annotations

import base64
from collections import OrderedDict
import hashlib
import os
import re
import threading
from typing import Optional
from urllib.parse import urlsplit

from . import safety

GEMINI_MODEL = "gemini-2.5-flash"
_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"  # NOTE-BIAS-OK: official Gemini API endpoint, not site bias
             f"{GEMINI_MODEL}:generateContent")

# Image discovery: markdown refs first (so we can anchor inline), then any bare
# image URL in the body (SPA/HTML/JSON-LD/og:image — the web-crawler-ocr net).
_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_IMG_URL_RE = re.compile(
    r"https?://[^\"\s'<>)]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\"\s'<>)]*)?",
    re.IGNORECASE,
)
_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}

_OCR_CACHE_MAX_SIZE = 256
_OCR_CACHE: OrderedDict[tuple[str, str, str, str], str] = OrderedDict()
_OCR_CACHE_LOCK = threading.Lock()
_PROMPT = (
    "이 이미지의 모든 텍스트를 정확하게 추출해주세요. 표/리스트는 마크다운으로 "
    "구조화하고, 제목·본문을 구분해 가독성 좋게 정리해주세요. 마크다운으로 출력."
)


def ocr_enabled() -> bool:
    return os.environ.get("INSANE_OCR", "") in ("1", "true", "yes")


def api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY") or None


def _mime_for(url: str) -> str:
    ext = os.path.splitext(urlsplit(url).path)[1].lower()
    return _MIME.get(ext, "image/jpeg")


def extract_image_urls(content: str, base_url: Optional[str] = None,
                       max_images: int = 6) -> list[str]:
    """Ordered, deduped, SSRF-safe image URLs (markdown refs prioritised)."""
    allow_private = safety.allow_private_default()
    out: list[str] = []
    seen: set[str] = set()

    def _add(u: str) -> None:
        u = u.strip()
        if not u or u in seen:
            return
        safe, _ = safety.classify_url(u, allow_private=allow_private)
        if not safe:
            return
        seen.add(u)
        out.append(u)

    for m in _MD_IMG_RE.finditer(content):
        _add(m.group(1))
    for m in _IMG_URL_RE.finditer(content):
        _add(m.group(0))
    return out[:max_images]


def _download(url: str, timeout: int) -> Optional[bytes]:
    """Fetch image bytes, or None on any failure (never raises).

    Uses safety.safe_get, which follows redirects manually and re-classifies
    every hop — so a 302 from a safe-looking image URL to a private/metadata
    address is blocked (the SSRF classification of the original URL alone is not
    enough once redirects are followed)."""
    try:
        r = safety.safe_get(url, impersonate="safari", timeout=timeout)
        if r is not None and r.status_code == 200 and r.content:
            return r.content
    except Exception:
        return None
    return None


def _ocr_one(image_bytes: bytes, mime: str, timeout: int) -> Optional[str]:
    """OCR one image via Gemini REST. None on failure. Monkeypatched in tests."""
    key = api_key()
    if not key:
        return None
    prompt_hash = hashlib.sha256(_PROMPT.encode("utf-8")).hexdigest()
    cache_key = (hashlib.sha256(image_bytes).hexdigest(), mime, GEMINI_MODEL, prompt_hash)
    with _OCR_CACHE_LOCK:
        cached = _OCR_CACHE.get(cache_key)
        if cached is not None:
            _OCR_CACHE.move_to_end(cache_key)
            return cached
    try:
        import requests
        data = base64.b64encode(image_bytes).decode()
        resp = requests.post(
            _ENDPOINT,
            headers={"x-goog-api-key": key},   # key in header, not URL (avoids log/trace leak)
            json={"contents": [{"parts": [
                {"text": _PROMPT},
                {"inline_data": {"mime_type": mime, "data": data}},
            ]}]},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        if text.strip():
            with _OCR_CACHE_LOCK:
                _OCR_CACHE[cache_key] = text
                _OCR_CACHE.move_to_end(cache_key)
                while len(_OCR_CACHE) > _OCR_CACHE_MAX_SIZE:
                    _OCR_CACHE.popitem(last=False)
        return text
    except Exception:
        return None


def _inline(content: str, ocr_map: dict[str, str]) -> str:
    """Insert an OCR block under each matching markdown image ref; append the
    rest in a trailing section."""
    lines = content.split("\n")
    result: list[str] = []
    matched: set[str] = set()
    for line in lines:
        result.append(line)
        m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if m and m.group(1) in ocr_map:
            url = m.group(1)
            matched.add(url)
            result.append("")
            result.append("> **[OCR]**")
            for ol in ocr_map[url].split("\n"):
                result.append(f"> {ol}")
            result.append("")
    leftover = [(u, t) for u, t in ocr_map.items() if u not in matched]
    if leftover:
        result.append("")
        result.append("---")
        result.append("## OCR extracted (unanchored images)")
        for u, t in leftover:
            result.append("")
            result.append(f"### {u}")
            result.append(t)
    return "\n".join(result)


def maybe_enrich(
    content: str,
    base_url: Optional[str] = None,
    *,
    timeout: int = 60,
    max_images: int = 6,
    force: bool = False,
) -> tuple[str, list[dict]]:
    """(enriched_content, trace). No-op (content unchanged) unless opted in,
    keyed, and images are present. `force=True` bypasses the env opt-in (the
    caller already decided via enable_ocr)."""
    trace: list[dict] = []
    if not content:
        return content, [{"skip": "empty_content"}]
    if not (force or ocr_enabled()):
        return content, [{"skip": "disabled"}]
    if not api_key():
        return content, [{"skip": "no_key"}]
    urls = extract_image_urls(content, base_url, max_images)
    if not urls:
        return content, [{"skip": "no_images"}]

    ocr_map: dict[str, str] = {}
    for u in urls:
        data = _download(u, timeout)
        if not data:
            trace.append({"url": u, "ok": False, "note": "download_failed"})
            continue
        text = _ocr_one(data, _mime_for(u), timeout)
        if text and text.strip():
            ocr_map[u] = text.strip()
            trace.append({"url": u, "ok": True, "chars": len(text)})
        else:
            trace.append({"url": u, "ok": False, "note": "ocr_failed"})

    if ocr_map:
        content = _inline(content, ocr_map)
    return content, trace
