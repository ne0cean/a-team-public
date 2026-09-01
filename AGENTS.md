# Agent Instructions

This repository is a public AI workflow toolkit. Treat it as a set of reusable
operating files, not as a production application.

## Entry Order

1. Read `llms.txt`.
2. Read `manifest.json`.
3. Read `docs/architecture.md`.
4. Find the right file via `docs/reference.md` (English catalog of every
   command and agent).
5. Read the specific command or agent file needed for the task.

## Operating Rules

- Preserve public-export hygiene: do not add credentials, private logs, local
  machine paths, or organization-specific endpoints.
- Keep workflow files portable. Use examples such as `/path/to/project`,
  `user@example.com`, and `example.com`.
- When editing command files, keep them executable by an AI assistant: explicit
  inputs, steps, outputs, and done criteria.
- When editing agent files, keep role boundaries clear: planner, executor,
  reviewer, QA, and operator are different responsibilities.
- Prefer small, reviewable changes over broad rewrites.

## Completion Standard

A change is complete when:

- the changed files are still public-safe,
- `manifest.json` remains accurate if structure changed,
- docs explain the new behavior or workflow,
- and any declared checks have been run or explicitly marked unavailable.
