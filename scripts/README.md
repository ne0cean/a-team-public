# scripts/

Some command files reference helper scripts (for example `scripts/vibe-init.sh`,
`scripts/mesh-scan.mjs`, `scripts/git-bridge.sh`). Those helpers live in the
private edition of this toolkit and are intentionally not exported: they are
tied to one person's machines, repos, and telemetry.

**The commands degrade gracefully without them.** Treat every script call you
cannot find as an optional automation step: read what the surrounding prose
says the step should establish, and let the agent establish it manually
(usually a few `git`/`ls`/`grep` calls). Nothing in the workflows depends on a
missing script for correctness — only for speed.

## What ships here

- `log-event.mjs` — a minimal, working event logger. Several commands call it
  to append usage telemetry; this version writes JSON lines to
  `.context/analytics.jsonl` so those calls succeed out of the box.

## Reimplementation contracts

If you want the full automation, the referenced helpers have small contracts:

| Script | Contract |
| --- | --- |
| `vibe-init.sh` | Print repo state: branch, last commit, dirty count, resume markers, suggested next commands. Read-only. |
| `mesh-scan.mjs` | Walk `.claude/` and report references between commands, agents, and hooks that point at missing files. Read-only. |
| `git-bridge.sh` | For repos with two remotes: fetch both, merge, push both. Fail loudly on conflict; never force-push. |
| `validate-blueprint.py` | Check a blueprint doc has the required sections; exit non-zero with a list of what is missing. |

Each is an afternoon project, and each is optional.
