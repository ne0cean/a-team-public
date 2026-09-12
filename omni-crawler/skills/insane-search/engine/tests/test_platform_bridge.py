"""Tests for the agent-reach platform bridge (Phase C) — deterministic + live."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import phase0, platform_bridge  # noqa: E402


_ORIG_RUN = platform_bridge.run


def setup_function(_):
    platform_bridge.reset_cache()
    platform_bridge.run = _ORIG_RUN   # undo any monkeypatch from a prior test


def test_detect_github_hosts():
    assert phase0._detect("https://github.com/cli/cli/issues/1") == "github"
    assert phase0._detect("https://gist.github.com/octocat/6cad326836d38bd3a7ae") == "github"
    # Non-github stays unrecognised.
    assert phase0._detect("https://example.com/x") is None


def test_issue_route_calls_gh(monkeypatch=None):
    calls = {}

    def fake_run(cmd, args, timeout):
        calls["cmd"], calls["args"] = cmd, args
        return True, "ISSUE BODY\nwith comments", "ok"

    platform_bridge.run = fake_run
    r = phase0._github("https://github.com/cli/cli/issues/42", timeout=10)
    assert r["ok"] is True
    assert r["route"] == "gh-issue"
    assert "ISSUE BODY" in r["content"]
    assert calls["cmd"] == "gh"
    assert calls["args"] == ["issue", "view", "42", "--repo", "cli/cli", "--comments"]


def test_pr_route_args():
    seen = {}

    def fake_run(cmd, args, timeout):
        seen["args"] = args
        return True, "PR", "ok"

    platform_bridge.run = fake_run
    r = phase0._github("https://github.com/torvalds/linux/pull/7", timeout=10)
    assert r["route"] == "gh-pr"
    assert seen["args"][:4] == ["pr", "view", "7", "--repo"]


def test_gist_route():
    def fake_run(cmd, args, timeout):
        assert args[:2] == ["gist", "view"]
        return True, "GIST", "ok"

    platform_bridge.run = fake_run
    r = phase0._github("https://gist.github.com/octocat/abc123", timeout=10)
    assert r["ok"] is True and r["route"] == "gh-gist"


def test_gist_flaglike_id_guarded():
    # A flag-like gist id must not be parsed as a gh flag — `--` guard required.
    seen = {}

    def fake_run(cmd, args, timeout):
        seen["args"] = args
        return True, "GIST", "ok"

    platform_bridge.run = fake_run
    phase0._github("https://gist.github.com/user/--config", timeout=10)
    assert "--" in seen["args"], "gist route must separate args with -- (arg injection guard)"
    assert seen["args"].index("--") < seen["args"].index("--config")


def test_bare_repo_falls_through():
    # A plain repo URL is git-clone's job, not the bridge's → ok=False.
    def fake_run(cmd, args, timeout):  # should not even be called for bare repo
        raise AssertionError("gh must not run for a bare repo URL")

    platform_bridge.run = fake_run
    r = phase0._github("https://github.com/cli/cli", timeout=10)
    assert r["ok"] is False and r["route"] is None


def test_missing_backend_graceful():
    platform_bridge.reset_cache()
    # Real run() against a definitely-absent backend → graceful (ok False, note).
    ok, out, note = platform_bridge.run("definitely-not-a-real-cli-xyz", ["x"], 5)
    assert ok is False and "not installed" in note


def test_live_gh_issue():
    """Live: fetch a real public issue THROUGH the engine bridge. Skips if gh
    absent/unauth/offline. Picks a real issue number dynamically (issue #1 is
    often a PR under GitHub's shared numbering, so hardcoding it is unreliable)."""
    import subprocess
    if shutil.which("gh") is None:
        print("SKIP test_live_gh_issue (gh not installed)")
        return
    try:
        p = subprocess.run(
            ["gh", "issue", "list", "--repo", "cli/cli", "--limit", "1",
             "--state", "all", "--json", "number", "-q", ".[0].number"],
            capture_output=True, text=True, timeout=30)
        num = (p.stdout or "").strip()
    except Exception as e:
        print(f"SKIP test_live_gh_issue ({type(e).__name__})")
        return
    if not num.isdigit():
        print(f"SKIP test_live_gh_issue (gh unauth/offline: {(p.stderr or '').strip()[:60]})")
        return
    platform_bridge.reset_cache()
    r = phase0._github(f"https://github.com/cli/cli/issues/{num}", timeout=40)
    assert r["ok"] is True and r["route"] == "gh-issue", r["attempts"]
    assert len(r["content"]) > 0
    print(f"PASS test_live_gh_issue (#{num}, {len(r['content'])} bytes via bridge)")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            setup_function(None)
            fn()
            if name != "test_live_gh_issue":
                print(f"PASS {name}")
    print("all platform_bridge tests passed")
