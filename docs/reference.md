# Reference Catalog

Every command and agent in this repository, with what it does and when to reach
for it. Command and agent files themselves are written in Korean (see the
language note in the README); this catalog is the English index.

## Commands (`.claude/commands/`)

Commands are repeatable procedures. An operator (or another agent) invokes them
like slash commands in Claude Code; each file spells out inputs, steps, checks,
and done criteria.

### Session lifecycle

| Command | What it does |
| --- | --- |
| `vibe.md` | Session start. Scans repo state (branch, dirty files, resume markers), loads `.context/` files, classifies next tasks, and proposes an execution mode. |
| `pickup.md` | Session resume. Detects what the previous session left behind and restores just enough context to continue, without a full reload. |
| `end.md` | Session close. Updates state files, verifies builds, commits, and pushes, so the next session (or another machine) can resume cleanly. |
| `zzz.md` | Unattended mode. Keeps working through a task list with explicit resume points, designed for overnight runs with safety rails. |

### Planning

| Command | What it does |
| --- | --- |
| `prd.md` | Takes a raw idea through validation questions into a written PRD. |
| `blueprint.md` | Produces a design document for an agent or automation system: context, workflow, implementation spec, then validates its structure. |
| `plan-eng.md` | Reviews an implementation plan from an engineering standpoint: risks, sequencing, missing tests. |
| `plan-ceo.md` | Reviews the same plan from a business standpoint: is this the right thing to build at all? |

### Build and verify

| Command | What it does |
| --- | --- |
| `tdd.md` | Red-green-refactor loop. Forces a failing test before any implementation. |
| `review.md` | Pre-landing review pipeline: standalone full review of a change before merge. |
| `ship.md` | Final gate before a PR: complete verification of the branch. |
| `qa.md` | Structured product QA across viewports and user flows, with screenshots and console checks. |
| `design.md` | Entry point to the design subsystem: briefing, generation, and audit for UI work. |

### Operations

| Command | What it does |
| --- | --- |
| `incident.md` | Failure response: detect, diagnose, recover, and write down what happened. |
| `doc-sync.md` | Finds drift between code and docs, then fixes the docs. |
| `mesh.md` | Health audit of the toolkit itself: are skills, agents, and hooks still wired to each other? |
| `prjt.md` | Portfolio status: reads each repo's `.context/CURRENT.md` and reports state and next tasks across projects. |
| `todo.md` | Lightweight personal notes that surface at the top of `prjt.md` output. |
| `daily-brief.md` | Daily briefing that combines external trend scanning with internal repo diagnostics. |

## Agents (`.claude/agents/`)

Agents are role prompts with explicit boundaries. The orchestrator dispatches
them; each returns structured output instead of editing outside its lane.

| Agent | Role | Touches code? |
| --- | --- | --- |
| `orchestrator.md` | Team lead. Decomposes a request into a parallel plan with file ownership, dispatches specialists, aggregates results. | Coordinates only |
| `pm.md` | Product manager. Defines requirements and scope before anyone implements; decides build-new vs extend-existing. | No |
| `architect.md` | System designer. Structure, stack, refactoring strategy. Returns design decisions, not code. | No |
| `designer.md` | Design briefing. Locks tone, variant, and density before UI generation, as the first gate against generic AI-looking output. | No |
| `coder.md` | Implementer. Works strictly inside its assigned file ownership, then verifies the build before reporting. | Yes |
| `tdd.md` | Test-first enforcer. Runs the red-green-refactor cycle and refuses to skip the failing-test step. | Yes |
| `reviewer.md` | Quality gate. Approves or rejects changes with structured findings. | No |
| `adversarial.md` | Attacker's-eye review. Reports exploit scenarios and weaknesses without touching the code. | No |
| `cso.md` | Security and system health audit (OWASP, STRIDE, architecture risk). Findings and recommendations only. | No |
| `qa.md` | Browser-automation QA across eight categories, producing a health score and classified issues. | No |
| `ui-inspector.md` | Visual verification. Screenshots, ARIA snapshots, and bounding boxes to diagnose layout and style problems cheaply. | No |
| `doc-sync.md` | Doc drift detector and fixer, agent form of the `doc-sync` command. | Docs only |

## How they combine

A typical flow chains them:

```
vibe → (prd | blueprint) → plan-eng → orchestrator
     → [pm → coder ∥ coder] → reviewer → qa → ship → end
```

The commands are the verbs an operator invokes; the agents are the specialists
those commands (or the orchestrator) delegate to. Nothing stops you from using
a single agent file standalone — each one is written to work in isolation.

## Templates and state files

| File | Purpose |
| --- | --- |
| `templates/context/ORIENT.md` | Facts about how to run the project: surfaces, deploy targets, run commands. |
| `templates/context/CURRENT.md` | Single source of truth for project state and next tasks. |
| `templates/context/RESUME.md` | Handoff note for the next session or machine. |
| `templates/context/DECISIONS.md` | Decision log, so agents stop re-litigating settled questions. |
| `templates/codex-brief.md` | Task brief for delegating implementation to an executor agent. |
