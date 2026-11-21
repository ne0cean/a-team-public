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
    ocr._OCR_CACHE.clear()
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


def test_identical_image_bytes_use_cached_gemini_result():
    import requests

    os.environ["GEMINI_API_KEY"] = "k"
    calls = {"n": 0}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"candidates": [{"content": {"parts": [{"text": "OCR text"}]}}]}

    def post(*args, **kwargs):
        calls["n"] += 1
        return Response()

    original_post = requests.post
    try:
        requests.post = post
        assert ocr._ocr_one(b"same image", "image/png", 1) == "OCR text"
        assert ocr._ocr_one(b"same image", "image/png", 2) == "OCR text"
        assert calls["n"] == 1
    finally:
        requests.post = original_post


def test_ocr_cache_key_includes_mime_and_prompt():
    import requests

    os.environ["GEMINI_API_KEY"] = "k"
    calls = []

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"candidates": [{"content": {"parts": [{"text": "OCR text"}]}}]}

    def post(*args, **kwargs):
        calls.append(kwargs["json"]["contents"][0]["parts"])
        return Response()

    original_post = requests.post
    original_prompt = ocr._PROMPT
    try:
        requests.post = post
        assert ocr._ocr_one(b"same image", "image/png", 1) == "OCR text"
        assert ocr._ocr_one(b"same image", "image/jpeg", 1) == "OCR text"
        ocr._PROMPT = original_prompt + " 추가 조건"
        assert ocr._ocr_one(b"same image", "image/jpeg", 1) == "OCR text"
        assert len(calls) == 3
        assert calls[0][1]["inline_data"]["mime_type"] == "image/png"
        assert calls[1][1]["inline_data"]["mime_type"] == "image/jpeg"
        assert calls[2][0]["text"] == original_prompt + " 추가 조건"
    finally:
        requests.post = original_post
        ocr._PROMPT = original_prompt


def test_empty_ocr_results_are_not_cached():
    import requests

    os.environ["GEMINI_API_KEY"] = "k"
    calls = {"n": 0}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"candidates": [{"content": {"parts": [{"text": "  \n "}]}}]}

    def post(*args, **kwargs):
        calls["n"] += 1
        return Response()

    original_post = requests.post
    try:
        requests.post = post
        assert ocr._ocr_one(b"empty result", "image/png", 1) == "  \n "
        assert ocr._ocr_one(b"empty result", "image/png", 1) == "  \n "
        assert calls["n"] == 2
    finally:
        requests.post = original_post


def test_ocr_cache_is_bounded_lru():
    import requests

    os.environ["GEMINI_API_KEY"] = "k"
    calls = {"n": 0}
    original_limit = ocr._OCR_CACHE_MAX_SIZE

    class Response:
        status_code = 200

        def __init__(self, text):
            self.text = text

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}

    def post(*args, **kwargs):
        calls["n"] += 1
        return Response(str(calls["n"]))

    original_post = requests.post
    try:
        ocr._OCR_CACHE_MAX_SIZE = 2
        requests.post = post
        assert ocr._ocr_one(b"a", "image/png", 1) == "1"
        assert ocr._ocr_one(b"b", "image/png", 1) == "2"
        assert ocr._ocr_one(b"a", "image/png", 1) == "1"  # Refresh a; b becomes least recent.
        assert ocr._ocr_one(b"c", "image/png", 1) == "3"
        assert len(ocr._OCR_CACHE) == 2
        assert ocr._ocr_one(b"b", "image/png", 1) == "4"  # b was evicted.
        assert calls["n"] == 4
    finally:
        requests.post = original_post
        ocr._OCR_CACHE_MAX_SIZE = original_limit


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
