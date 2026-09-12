"""Deterministic tests for the Anubis PoW solver (A-Team omni-crawler)."""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import anubis  # noqa: E402


def test_pow_leading_zeroes_and_verifiable():
    challenge = "a-team-omni-crawler-test-challenge"
    for diff in (1, 2, 3, 4):
        nonce, digest = anubis.solve_pow(challenge, diff)
        assert digest.startswith("0" * diff)
        assert hashlib.sha256(f"{challenge}{nonce}".encode()).hexdigest() == digest


def test_pow_deterministic():
    c = "abc"
    assert anubis.solve_pow(c, 3)[0] == anubis.solve_pow(c, 3)[0]


def test_pow_difficulty_cap_refused():
    try:
        anubis.solve_pow("abc", anubis.MAX_DIFFICULTY + 1)
        assert False, "should have refused"
    except ValueError as e:
        assert "cap" in str(e)


def test_parse_object_challenge():
    # Live v1.2x shape: challenge is an object with randomData + id.
    html = ('<html><script id="anubis_challenge" type="application/json">'
            '{"rules":{"algorithm":"fast","difficulty":5},'
            '"challenge":{"randomData":"deadbeef","id":"uuid-1","difficulty":5}}'
            '</script></html>')
    assert anubis.parse_challenge(html) == {
        "data": "deadbeef", "difficulty": 5, "id": "uuid-1"}


def test_parse_legacy_string_challenge():
    html = ('<html><script id="anubis_challenge" type="application/json">'
            '{"challenge":"abc123","rules":{"difficulty":4}}</script></html>')
    assert anubis.parse_challenge(html) == {
        "data": "abc123", "difficulty": 4, "id": None}


def test_parse_missing_returns_none():
    assert anubis.parse_challenge("<html>nothing here</html>") is None


def test_detection_true_and_no_false_positive():
    hit = ('<script id="anubis_challenge" type="application/json">'
           '{"challenge":"x","rules":{"difficulty":1}}</script>')
    assert anubis.looks_like_anubis(hit) is True
    # An article merely mentioning the Egyptian god must not trip detection.
    assert anubis.looks_like_anubis("<html>anubis was a god of the dead</html>") is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  {name} OK")
    print("PASS")
