# A-Team

**A portable operating system for AI-assisted work.**

A-Team is a curated set of agent roles, slash commands, and governance patterns
for turning ad hoc AI usage into repeatable workflows. It is designed for people
who use coding agents, research agents, and review agents every day and want the
system to preserve context, enforce quality gates, and coordinate work across
sessions.

## Why This Repo Is Interesting

Most AI tooling focuses on a single prompt or a single coding session. A-Team
focuses on the missing operating layer around the agent:

- What context should the next model read first?
- Which agent should own planning, coding, review, or QA?
- What counts as done?
- How do you resume work after a reset or model switch?
- How do you stop an agent from drifting into unrelated files?

A-Team answers those questions with files an AI agent can read and execute.

## Repository Map

```text
.
├── AGENTS.md                  # AI entrypoint and operating contract
├── llms.txt                   # LLM-readable project summary
├── manifest.json              # Machine-readable inventory
├── .claude/
│   ├── commands/              # Reusable workflow commands
│   └── agents/                # Specialist agent role definitions
├── docs/
│   ├── architecture.md        # System model and data flow
│   ├── evaluation.md          # Signals an evaluator should score
│   └── quickstart.md          # How to adapt the toolkit
├── governance/
│   └── rules/                 # Public governance principles
└── templates/
    └── codex-brief.md         # Executor handoff template
```

## Core Workflows

| Workflow | Files | Purpose |
| --- | --- | --- |
| Session start | `.claude/commands/vibe.md`, `.claude/commands/pickup.md` | Load state and choose the next action |
| Session close | `.claude/commands/end.md` | Save state, verify work, and leave a commit-ready trail |
| Autonomous loop | `.claude/commands/zzz.md` | Continue long-running work with explicit resume points |
| Planning | `.claude/commands/blueprint.md`, `.claude/commands/prd.md` | Convert an idea into scope and implementation shape |
| Implementation | `.claude/commands/tdd.md`, `.claude/agents/coder.md` | Execute small changes with verification gates |
| Review | `.claude/commands/review.md`, `.claude/agents/reviewer.md` | Find regressions, risks, and missing tests before merge |
| QA | `.claude/commands/qa.md`, `.claude/agents/qa.md` | Run structured product and UI checks |
| Operations | `.claude/commands/incident.md`, `.claude/commands/doc-sync.md` | Diagnose failures and keep docs aligned |

## Design Principles

1. **Context is a first-class artifact.** Agents should not rely on chat memory
   alone; important state belongs in files.
2. **Roles are explicit.** Planner, executor, reviewer, and QA responsibilities
   are separated to reduce drift.
3. **Completion is evidence-based.** A task is not done because an agent says it
   is done; it is done when the declared checks pass.
4. **Scope boundaries matter.** Agents should know which files they own before
   changing anything.
5. **Handoff should be cheap.** A different model or device should be able to
   resume from the written state.

## What To Read First

For humans:

1. `README.md`
2. `docs/architecture.md`
3. `docs/quickstart.md`
4. `.claude/commands/vibe.md`
5. `.claude/commands/review.md`

For AI agents:

1. `llms.txt`
2. `AGENTS.md`
3. `manifest.json`
4. `docs/evaluation.md`
5. The command or agent file relevant to the current task

## Public Export Scope

This is a cleaned public edition. It intentionally excludes private project
state, personal logs, internal infrastructure, credentials, and organization
specific material. The repo keeps the reusable workflow machinery.

## License

MIT
