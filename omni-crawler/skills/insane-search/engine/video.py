"""Video transcript route — A-Team omni-crawler addition (Phase E).

phase0._youtube returns yt-dlp's `--dump-json` metadata, which already lists the
video's caption tracks under `subtitles` / `automatic_captions`. This module
turns those into readable transcript text: pick a track for a preferred
language, download the WebVTT via the SSRF-safe fetcher, and strip it to plain
text. Opt-in (INSANE_TRANSCRIPT=1) so the default youtube route is unchanged.

SCOPE / SAFETY:
  * Public captions only. The heavier "SSO video → yt-dlp --cookies-from-browser
    → Whisper transcription" cascade is deliberately NOT implemented here:
    reading the user's browser cookies for arbitrary sites is a privacy hazard,
    and Whisper is a heavy dependency. Deferred to roadmap (see NOTICE.md).
  * Caption tracks are downloaded through safety.safe_get (per-hop SSRF
    re-classification), never a raw follow-redirects GET.
  * A single track is fetched — no bulk/multi-lang scraping.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from . import safety

DEFAULT_LANGS = ["en", "ko"]
# Caption formats we can turn into text, best first.
_FMT_RANK = {"vtt": 0, "srv3": 1, "srv2": 2, "srv1": 3, "ttml": 4, "json3": 5}

_TS_RE = re.compile(r"-->")
_TAG_RE = re.compile(r"<[^>]+>")


def transcript_enabled() -> bool:
    return os.environ.get("INSANE_TRANSCRIPT", "") in ("1", "true", "yes")


def preferred_langs() -> list[str]:
    raw = os.environ.get("INSANE_TRANSCRIPT_LANGS", "")
    return [x.strip() for x in raw.split(",") if x.strip()] or DEFAULT_LANGS


def _lang_matches(track_lang: str, want: str) -> bool:
    tl = track_lang.lower()
    return tl == want or tl.startswith(want + "-")


def pick_caption_url(info: dict, langs: Optional[list[str]] = None) -> Optional[str]:
    """Choose one caption track URL from a yt-dlp info dict. Manual `subtitles`
    beat `automatic_captions`; within a language, the most text-friendly format
    wins. Returns None when no usable track exists."""
    langs = langs or preferred_langs()
    for source in ("subtitles", "automatic_captions"):
        tracks = info.get(source) or {}
        if not isinstance(tracks, dict):
            continue
        for want in langs:
            for track_lang, fmts in tracks.items():
                if not _lang_matches(str(track_lang), want) or not isinstance(fmts, list):
                    continue
                ranked = sorted(
                    (f for f in fmts if isinstance(f, dict) and f.get("url")),
                    key=lambda f: _FMT_RANK.get(str(f.get("ext", "")).lower(), 99),
                )
                if ranked:
                    return ranked[0]["url"]
    return None


def vtt_to_text(vtt: str) -> str:
    """Strip a WebVTT/SRT caption body to deduped plain text."""
    out: list[str] = []
    for raw in vtt.splitlines():
        line = _TAG_RE.sub("", raw).strip()
        if not line or line == "WEBVTT" or _TS_RE.search(line):
            continue
        if line.isdigit():                      # SRT cue index
            continue
        if line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        if not out or out[-1] != line:          # collapse repeated caption lines
            out.append(line)
    return "\n".join(out)


def _download_text(url: str, timeout: int) -> Optional[str]:
    """SSRF-safe caption download. None on any failure. Monkeypatched in tests."""
    try:
        r = safety.safe_get(url, impersonate="safari", timeout=timeout)
        if r is not None and r.status_code == 200:
            return r.text or ""
    except Exception:
        return None
    return None


def transcript_from_info(info_json: str, *, timeout: int = 30,
                         langs: Optional[list[str]] = None) -> tuple[Optional[str], dict]:
    """(transcript_text, trace) from a yt-dlp --dump-json string. None text on
    no-track / download-failure / parse error — never raises."""
    try:
        info = json.loads(info_json)
    except Exception:
        return None, {"skip": "bad_json"}
    url = pick_caption_url(info, langs)
    if not url:
        return None, {"skip": "no_captions"}
    body = _download_text(url, timeout)
    if not body:
        return None, {"ok": False, "note": "caption_download_failed"}
    text = vtt_to_text(body)
    if not text.strip():
        return None, {"ok": False, "note": "empty_transcript"}
    return text, {"ok": True, "chars": len(text)}


def maybe_append_transcript(content: str, info_json: str, *, timeout: int = 30,
                            force: bool = False) -> str:
    """Append a `## Transcript` section to `content` when opted in and a caption
    track is available. No-op otherwise (returns content unchanged)."""
    if not (force or transcript_enabled()):
        return content
    text, _trace = transcript_from_info(info_json, timeout=timeout)
    if not text:
        return content
    return f"{content}\n\n---\n## Transcript\n\n{text}"
