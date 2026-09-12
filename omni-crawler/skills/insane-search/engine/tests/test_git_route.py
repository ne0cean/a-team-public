"""Deterministic tests for the git-clone-first route detector (A-Team)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.git_route import detect_git_repo  # noqa: E402


def test_bare_github_gitlab():
    assert detect_git_repo("https://github.com/octocat/Hello-World") == \
        "https://github.com/octocat/Hello-World.git"
    assert detect_git_repo("https://gitlab.com/foo/bar/") == \
        "https://gitlab.com/foo/bar.git"


def test_dot_git_suffix_preserved():
    assert detect_git_repo("https://github.com/octocat/Hello-World.git") == \
        "https://github.com/octocat/Hello-World.git"


def test_cgit_view_derives_repo():
    # The abuse pattern the article names: cgit commit/tree views → clone URL.
    base = "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git"
    assert detect_git_repo(base + "/commit/?id=abc123") == base
    assert detect_git_repo(base + "/tree/kernel") == base


def test_hosted_subpage_not_hijacked():
    # A request for a specific hosted page must NOT be turned into a repo card.
    assert detect_git_repo("https://github.com/octocat/Hello-World/issues/1") is None
    assert detect_git_repo("https://github.com/octocat/Hello-World/blob/main/README") is None


def test_non_git_url():
    assert detect_git_repo("https://example.com/article") is None
    assert detect_git_repo("not-a-url") is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  {name} OK")
    print("PASS")
