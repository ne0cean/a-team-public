"""Deterministic tests for the OCR enrichment layer (Phase D). No network/API."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import ocr  # noqa: E402

_ORIG_DOWNLOAD = ocr._download
_ORIG_OCR_ONE = ocr._ocr_one


def setup_function(_):
    ocr._download = _ORIG_DOWNLOAD
    ocr._ocr_one = _ORIG_OCR_ONE
    os.environ.pop("INSANE_OCR", None)
    os.environ.pop("GEMINI_API_KEY", None)


def teardown_function(_):
    setup_function(_)


def _stub_pipeline(text="EXTRACTED TEXT"):
    ocr._download = lambda url, timeout: b"\x89PNGfake"
    ocr._ocr_one = lambda data, mime, timeout: text


def test_disabled_is_noop():
    _stub_pipeline()
    os.environ["GEMINI_API_KEY"] = "k"
    md = "![pic](https://example.com/a.png)"
    out, trace = ocr.maybe_enrich(md, "https://example.com")  # not forced, env unset
    assert out == md
    assert trace == [{"skip": "disabled"}]


def test_no_key_skips_even_when_forced():
    _stub_pipeline()
    md = "![pic](https://example.com/a.png)"
    out, trace = ocr.maybe_enrich(md, force=True)
    assert out == md and trace == [{"skip": "no_key"}]


def test_no_images_skips():
    os.environ["GEMINI_API_KEY"] = "k"
    out, trace = ocr.maybe_enrich("just text, no pictures", force=True)
    assert trace == [{"skip": "no_images"}]


def test_inline_under_markdown_ref():
    _stub_pipeline("TABLE\n| a | b |")
    os.environ["GEMINI_API_KEY"] = "k"
    md = "# Title\n\n![pic](https://example.com/a.png)\n\ntail"
    out, trace = ocr.maybe_enrich(md, force=True)
    assert "> **[OCR]**" in out
    assert "> TABLE" in out
    assert out.index("> TABLE") > out.index("![pic]")   # inserted AFTER the ref
    assert out.index("tail") > out.index("> TABLE")      # and before the tail
    assert trace[0]["ok"] is True


def test_unanchored_image_appended():
    _stub_pipeline("SIGN TEXT")
    os.environ["GEMINI_API_KEY"] = "k"
    # Bare URL (no markdown ref) → appended in trailing section, not inlined.
    html = 'body <img src="x"> https://example.com/banner.jpg more'
    out, trace = ocr.maybe_enrich(html, force=True)
    assert "## OCR extracted (unanchored images)" in out
    assert "SIGN TEXT" in out


def test_ssrf_image_skipped():
    os.environ["GEMINI_API_KEY"] = "k"
    called = {"n": 0}
    ocr._download = lambda url, timeout: called.__setitem__("n", called["n"] + 1) or b"x"
    ocr._ocr_one = lambda *a: "T"
    md = "![p](http://169.254.169.254/latest/meta-data/a.png)"  # cloud metadata
    out, trace = ocr.maybe_enrich(md, force=True)
    assert called["n"] == 0                 # never downloaded the SSRF target
    assert trace == [{"skip": "no_images"}]  # filtered out before download


def test_max_images_cap():
    urls = "\n".join(f"![p{i}](https://example.com/{i}.png)" for i in range(20))
    got = ocr.extract_image_urls(urls, "https://example.com", max_images=6)
    assert len(got) == 6


def test_download_failure_recorded():
    os.environ["GEMINI_API_KEY"] = "k"
    ocr._download = lambda url, timeout: None
    ocr._ocr_one = lambda *a: "unused"
    md = "![p](https://example.com/a.png)"
    out, trace = ocr.maybe_enrich(md, force=True)
    assert out == md                        # nothing inlined
    assert trace[0]["ok"] is False and trace[0]["note"] == "download_failed"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            setup_function(None)
            fn()
            teardown_function(None)
            print(f"PASS {name}")
    print("all ocr tests passed")
