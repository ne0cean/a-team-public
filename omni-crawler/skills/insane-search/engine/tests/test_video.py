"""Deterministic tests for the video transcript route (Phase E). No network."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import video  # noqa: E402

_ORIG_DL = video._download_text


def setup_function(_):
    video._download_text = _ORIG_DL
    os.environ.pop("INSANE_TRANSCRIPT", None)
    os.environ.pop("INSANE_TRANSCRIPT_LANGS", None)


def teardown_function(_):
    setup_function(_)


_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
Hello world

00:00:03.000 --> 00:00:05.000
Hello world

00:00:05.000 --> 00:00:07.000
<c>second</c> line
"""


def test_vtt_to_text_strips_and_dedupes():
    out = video.vtt_to_text(_VTT)
    assert out == "Hello world\nsecond line"   # header/timestamps/tags gone, dupe collapsed


def test_pick_caption_prefers_manual_then_format():
    info = {
        "subtitles": {"en": [{"ext": "json3", "url": "M_JSON3"}, {"ext": "vtt", "url": "M_VTT"}]},
        "automatic_captions": {"en": [{"ext": "vtt", "url": "AUTO_VTT"}]},
    }
    # manual beats auto; within manual, vtt (rank 0) beats json3
    assert video.pick_caption_url(info, ["en"]) == "M_VTT"


def test_pick_caption_lang_priority_and_prefix():
    info = {"automatic_captions": {
        "ko": [{"ext": "vtt", "url": "KO"}],
        "en-US": [{"ext": "vtt", "url": "EN_US"}],
    }}
    assert video.pick_caption_url(info, ["en", "ko"]) == "EN_US"   # en matches en-US prefix, first pref
    assert video.pick_caption_url(info, ["ko"]) == "KO"


def test_pick_caption_none_when_absent():
    assert video.pick_caption_url({"subtitles": {}}, ["en"]) is None
    assert video.pick_caption_url({}, ["en"]) is None


def test_transcript_from_info_happy():
    video._download_text = lambda url, timeout: _VTT
    info = json.dumps({"subtitles": {"en": [{"ext": "vtt", "url": "U"}]}})
    text, tr = video.transcript_from_info(info)
    assert "Hello world" in text and tr["ok"] is True


def test_transcript_from_info_no_captions():
    info = json.dumps({"subtitles": {}, "automatic_captions": {}})
    text, tr = video.transcript_from_info(info)
    assert text is None and tr == {"skip": "no_captions"}


def test_transcript_from_info_bad_json():
    text, tr = video.transcript_from_info("not json")
    assert text is None and tr == {"skip": "bad_json"}


def test_download_failure_recorded():
    video._download_text = lambda url, timeout: None
    info = json.dumps({"subtitles": {"en": [{"ext": "vtt", "url": "U"}]}})
    text, tr = video.transcript_from_info(info)
    assert text is None and tr["note"] == "caption_download_failed"


def test_maybe_append_disabled_is_noop():
    video._download_text = lambda url, timeout: _VTT
    info = json.dumps({"subtitles": {"en": [{"ext": "vtt", "url": "U"}]}})
    content = "METADATA"
    assert video.maybe_append_transcript(content, info) == content   # env unset, not forced


def test_maybe_append_forced():
    video._download_text = lambda url, timeout: _VTT
    info = json.dumps({"subtitles": {"en": [{"ext": "vtt", "url": "U"}]}})
    out = video.maybe_append_transcript("METADATA", info, force=True)
    assert out.startswith("METADATA")
    assert "## Transcript" in out and "Hello world" in out


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            setup_function(None)
            fn()
            teardown_function(None)
            print(f"PASS {name}")
    print("all video tests passed")
