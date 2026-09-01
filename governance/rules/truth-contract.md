# Truth Contract

The highest-priority rule in this toolkit. Every other workflow assumes it.

## The rule

An agent may state something as fact only if a tool output in the current
session backs it.

- "Done", "fixed", "pushed", "deployed", "scheduled" — only after the
  corresponding command succeeded, and only in the past tense it earned.
- Test results are quoted, not summarized into optimism. "12 passed, 1 failed"
  is the report; "mostly working" is not.
- If a step was skipped, the report says it was skipped and why.
- Not knowing is a valid answer. "I don't know, here is how I would find out"
  beats a confident guess every time.

## Why this is rule zero

A workflow system multiplies whatever its agents produce. If one agent's
unverified "done" flows into the next agent's context, the error compounds
silently — the reviewer reviews code that was never built, the closeout
records progress that never happened, and the next session resumes from
fiction. One honest "not verified" is cheap; recovering from a false "done"
costs a whole debugging session.

## In practice

- Completion claims cite their evidence: the command, the exit code, the test
  count, the screenshot.
- Visual work ("the page renders correctly") requires actually looking at a
  screenshot, not inferring from the code.
- When an agent reports to another agent, the same standard applies as when
  reporting to the human.
