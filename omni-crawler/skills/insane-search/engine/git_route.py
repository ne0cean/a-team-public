"""git-clone-first route — A-Team omni-crawler addition.

When a URL points at a git repository (a bare repo, a `*.git` URL, or a cgit /
gitweb commit/tree/log view), cloning the repo once is dramatically cheaper for
the origin than scraping HTML commit-by-commit. This is the approach the git
host maintainer explicitly asks scrapers to use, in the "creepy-crawlies" essay
that motivated this feature:
    "the stupidest possible way — rendering everything as HTML commit by commit.
     ...Clone the repos, walk every commit. Done."
    (full citation in NOTICE.md)

SAFETY / SCOPE:
  * ONE shallow, partial clone (`--depth N --filter=blob:none`) per call. Blobs
    are fetched lazily (only the README we read), so even linux.git stays small.
  * NOT for multi-node / repeated cloning — the same article calls that "awful";
    run a local mirror for repeat use.
  * git hooks + fsmonitor disabled on clone (a hostile repo must not run code).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional
from urllib.parse import urlparse

# cgit / gitweb view segments that sit *after* the repo path — stripped to reach
# the cloneable repo root.
_CGIT_VIEWS = ("commit", "tree", "log", "diff", "refs", "snapshot", "plain",
               "about", "summary", "tag", "patch", "atom", "blame")

_GITHUB_GITLAB_BARE = re.compile(
    r"^https?://(?:www\.)?(github|gitlab)\.com/[^/]+/[^/]+/?$", re.IGNORECASE)

# Sub-pages where the user wants THAT page, not a repo card (do not hijack).
_HOSTED_SUBPAGE = re.compile(
    r"^https?://(?:www\.)?(github|gitlab)\.com/[^/]+/[^/]+/"
    r"(issues|pull|pulls|merge_requests|blob|tree|wiki|releases|actions|discussions|settings)\b",
    re.IGNORECASE)


def detect_git_repo(url: str) -> Optional[str]:
    """Return a cloneable URL if `url` is a git repository (or a cgit/gitweb
    view of one), else None.

    Rules (conservative — avoid hijacking a request for a specific hosted page):
      * a bare owner/repo on GitHub/GitLab                     -> .../repo.git
      * any URL containing `<repo>.git` (optionally + cgit view) -> <repo>.git
      * a cgit-style /pub/scm/.../<repo>.git/... path          -> the .git URL
      * GitHub/GitLab sub-pages (/issues, /blob, ...)          -> None
    """
    if not url or not url.lower().startswith(("http://", "https://")):
        return None

    # Never hijack an explicit hosted sub-page request.
    if _HOSTED_SUBPAGE.match(url):
        return None

    # 1) Bare GitHub/GitLab repo.
    m = _GITHUB_GITLAB_BARE.match(url)
    if m:
        base = url.rstrip("/")
        return base if base.endswith(".git") else base + ".git"

    # 2) Any `<repo>.git` in the path (covers cgit, gitweb, self-hosted forges).
    #    Keep scheme://host + path up to and including `.git`.
    parsed = urlparse(url)
    path = parsed.path
    idx = path.find(".git")
    if idx != -1:
        repo_path = path[: idx + len(".git")]
        return f"{parsed.scheme}://{parsed.netloc}{repo_path}"

    # 3) cgit view without an explicit `.git` (e.g. /cgit/<repo>/commit/?id=..).
    #    Strip a trailing recognised view segment to reach the repo root.
    segs = [s for s in path.split("/") if s]
    for i, seg in enumerate(segs):
        if seg in _CGIT_VIEWS and i > 0:
            repo_path = "/" + "/".join(segs[:i])
            # Only treat as a repo if the host looks like a git service.
            if any(k in parsed.netloc for k in ("git", "cgit", "gitweb", "scm")):
                return f"{parsed.scheme}://{parsed.netloc}{repo_path}"
            break
    return None


def _run(cmd: list[str], *, cwd: Optional[str] = None, timeout: int = 120) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def clone_to_card(clone_url: str, source_url: str, *, depth: int = 50,
                  timeout: int = 180, log_count: int = 50,
                  logger=None) -> Optional[str]:
    """Shallow+partial clone `clone_url` and return a markdown "repo card"
    (metadata + recent commit log + README). Returns None on failure.
    """
    def _log(m):
        if logger:
            logger(f"[git] {m}")

    if not shutil.which("git"):
        _log("git binary not found")
        return None

    tmp = tempfile.mkdtemp(prefix="omni-git-")
    dest = os.path.join(tmp, "repo")
    try:
        # hooks + fsmonitor disabled: a hostile repo must not execute code.
        clone = [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=",
            "clone", "--depth", str(depth), "--filter=blob:none", "--no-tags",
            "--quiet", clone_url, dest,
        ]
        rc, _out, err = _run(clone, timeout=timeout)
        if rc != 0:
            _log(f"clone failed rc={rc}: {err.strip()[:160]}")
            return None
        _log(f"cloned (depth={depth}, blob:none): {clone_url}")

        # Metadata
        def _git(args, tmo=30):
            return _run(["git", "-C", dest] + args, timeout=tmo)

        _, branch, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"])
        _, head, _ = _git(["log", "-1", "--format=%H%n%an%n%ad%n%s", "--date=short"])
        _, log, _ = _git(["log", f"-{log_count}", "--format=- `%h` %s (%an, %ad)", "--date=short"])

        head_lines = head.strip().splitlines()
        commit_sha = head_lines[0] if head_lines else "?"
        author = head_lines[1] if len(head_lines) > 1 else "?"
        cdate = head_lines[2] if len(head_lines) > 2 else "?"
        subject = head_lines[3] if len(head_lines) > 3 else ""

        # README (triggers exactly one lazy blob fetch)
        readme_text = ""
        readme_name = ""
        try:
            _, files, _ = _git(["ls-tree", "--name-only", "HEAD"])
            for name in files.splitlines():
                if name.lower().startswith("readme"):
                    rc2, blob, _ = _git(["show", f"HEAD:{name}"], tmo=45)
                    if rc2 == 0:
                        readme_name, readme_text = name, blob
                    break
        except Exception as e:  # noqa: BLE001
            _log(f"readme fetch skipped: {e}")

        card = [
            f"# git repo: {clone_url.rsplit('/', 1)[-1]}",
            "",
            f"> Source: {source_url}",
            f"> Clone: {clone_url}",
            f"> Method: git-clone-first (shallow depth={depth}, blob:none) — "
            f"server-friendly extraction, not HTML commit scraping",
            "",
            f"- **Default branch**: {branch.strip() or '?'}",
            f"- **HEAD**: `{commit_sha[:12]}` — {subject} ({author}, {cdate})",
            "",
            f"## Recent commits (last {log_count})",
            "",
            log.strip() or "_(none)_",
            "",
        ]
        if readme_text:
            card += [f"## {readme_name}", "", readme_text.strip(), ""]
        return "\n".join(card)
    except subprocess.TimeoutExpired:
        _log("clone/log timed out")
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
