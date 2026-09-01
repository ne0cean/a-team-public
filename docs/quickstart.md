# Quickstart

You do not install A-Team. You copy the parts you want and adapt them. This
page is the ten-minute version.

## Minute 0–3: pick one workflow

Open `docs/reference.md` and pick the single command that matches your most
annoying recurring task. Good first picks:

- You lose context between sessions → `vibe.md` + `end.md` (adopt as a pair)
- Your agent writes code before tests → `tdd.md`
- Your agent's "done" doesn't survive review → `review.md`
- Your agent wanders into unrelated files → `agents/orchestrator.md` + `governance/rules/scope-ownership.md`

## Minute 3–6: wire it into your project

```bash
# from your project root
mkdir -p .claude/commands .context
cp path/to/a-team-public/.claude/commands/tdd.md .claude/commands/
cp path/to/a-team-public/templates/context/CURRENT.md .context/CURRENT.md
```

Fill `.context/CURRENT.md` with two or three real tasks. Honest ones — an
agent will pick the top item and start.

## Minute 6–10: run it

Open your coding agent (Claude Code reads `.claude/commands/` natively; any
agent that can read files works) and invoke the command. Then adapt:

- Replace example paths with your project's paths.
- Replace the test commands with your stack's commands.
- Delete steps that reference helpers you don't have — `scripts/README.md`
  explains what each missing helper was supposed to establish, so you can
  keep the step manually or drop it.

## What to adopt second

The pieces compound in this order:

1. **State files** (`templates/context/`) — the biggest single upgrade.
   `ORIENT.md` stops re-explaining your project every session; `RESUME.md`
   makes machine switches free; `DECISIONS.md` stops re-litigating settled
   questions.
2. **Session bookends** (`vibe.md` / `end.md`) — once state files exist,
   these keep them alive automatically.
3. **A review gate** (`review.md` or `agents/reviewer.md`) — separate the
   agent that writes from the agent that judges.
4. **The truth contract** (`governance/rules/truth-contract.md`) — paste it
   into your project's agent instructions verbatim. It is one page and it
   changes the tone of every report you get.

## Sanity rules while adapting

- Keep one source of truth for current state (one `CURRENT.md`, not three).
- Keep done criteria executable: a command that exits 0, not a vibe.
- When a workflow file and reality disagree, fix the file in the same session
  — drift between docs and practice is how systems rot (that is what
  `mesh.md` and `doc-sync.md` exist to catch).
