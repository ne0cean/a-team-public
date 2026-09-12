"""Platform bridge — generic subprocess mechanism for agent-reach backends.

Phase 0 (phase0.py) recognises platform hosts and picks a route; this module is
the *mechanism* half — it shells out to the per-platform backend CLIs that
agent-reach installs (gh, yt-dlp, twitter-cli, OpenCLI, …). Keeping the
mechanism here (and all host-name / URL parsing in phase0.py) preserves the
"only phase0 names hosts" isolation invariant enforced by bias_check.

Design:
  * Backend availability is probed once and cached; a missing backend is a
    graceful skip, never an exception — the caller falls through to the grid.
  * No network/auth assumptions: each runner returns (ok, output, note) so
    phase0 can record the attempt whether it succeeds or not.
  * Scope stays read-only. No posting/commenting; agent-reach's write surface
    is deliberately not bridged.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional

_AVAIL_CACHE: dict[str, bool] = {}


def backend_available(cmd: str) -> bool:
    """True if backend CLI `cmd` is on PATH (cached per run)."""
    if cmd not in _AVAIL_CACHE:
        _AVAIL_CACHE[cmd] = shutil.which(cmd) is not None
    return _AVAIL_CACHE[cmd]


def run(cmd: str, args: list[str], timeout: int) -> tuple[bool, str, str]:
    """Run `cmd args`. Returns (ok, stdout, note). Never raises.

    ok = process exited 0 with non-empty stdout. note carries a short failure
    reason (truncated stderr / exception name / 'not installed')."""
    if not backend_available(cmd):
        return False, "", f"{cmd} not installed"
    try:
        p = subprocess.run(
            [cmd, *args], capture_output=True, text=True, timeout=timeout,
        )
        out = p.stdout or ""
        if p.returncode == 0 and out.strip():
            return True, out, "ok"
        return False, out, (p.stderr or "").strip()[:120] or f"exit={p.returncode}"
    except subprocess.TimeoutExpired:
        return False, "", f"timeout>{timeout}s"
    except Exception as e:  # runner must never break the chain
        return False, "", f"{type(e).__name__}"


def reset_cache() -> None:
    _AVAIL_CACHE.clear()
