# Worked Example — One Day Through the Toolkit

A realistic walkthrough of how the pieces fit together on a small web project.
Names and outputs are illustrative; the file flow is the real system.

## 09:10 — Session start

The operator opens Claude Code in the project and invokes `vibe.md`.

The command scans state and reports:

```
last commit: a1b2c3d "feat: add invoice export"
branch: main, clean
.context/CURRENT.md — Next: [ ] CSV export drops rows with commas in names
resume marker: none
mode: single terminal, implementation task
```

Because the top task is a bug with a clear reproduction, the session goes
straight to `tdd.md`.

## 09:20 — Red

The TDD loop writes a failing test first:

```
✗ exports names containing commas intact  (expected 3 rows, got 2)
```

The failing run is the point. Implementation before a red test is a rule
violation, and the tdd agent refuses to proceed without it.

## 09:40 — Green, then review

Minimal fix goes in, the test passes, and the loop runs the full suite.
Then `review.md` is invoked. The reviewer agent reads only the diff and
returns structured findings:

```
BLOCKER: none
WARN: escaping helper duplicates util/csv.ts:41 — reuse instead
```

The operator accepts the warning, the coder agent applies the reuse, and the
suite runs again.

## 11:00 — A bigger request arrives

"Add a shareable dashboard page" is not a one-file fix, so the operator invokes
the orchestrator agent instead of coding directly. The orchestrator produces a
plan before any code:

```
PARALLEL_PLAN.md
  task 1 (pm): scope — what must be on the page, what explicitly not
  task 2 (designer): tone brief before any UI generation
  task 3 (coder): page skeleton     — owns src/pages/dashboard/*
  task 4 (coder): data endpoint     — owns src/api/dashboard.ts
  gate: reviewer on the combined diff, then qa on the running page
```

File ownership is written down first, so the two coder agents cannot collide.
The qa agent later loads the page in a browser, captures desktop and mobile
screenshots, and files one layout issue; ui-inspector pins it to an overflow
on a flex container.

## 17:50 — Session close

`end.md` runs the closeout:

1. `.context/CURRENT.md` — bug task checked off, dashboard tasks updated with
   what is done and what remains.
2. `.context/RESUME.md` — one in-flight item recorded: "mobile overflow fix
   applied, not yet re-verified on real device widths."
3. Build and tests verified, work committed, pushed.

## Next morning

A different machine, a fresh session. `pickup.md` finds the resume note and
starts with exactly one action: re-run qa on the dashboard at mobile widths.
Nothing from yesterday's chat context is needed. That is the point of the
system: the repository, not the conversation, carries the state.
