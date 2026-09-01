# Scope Ownership

The rule that makes parallel agents safe.

## The rule

Before any agent modifies files, ownership is written down: which paths this
task owns, and that everything outside the list is read-only.

- The orchestrator assigns ownership in the plan (one section per task) before
  dispatching any coder.
- Two concurrent tasks never share a writable path. If they seem to need to,
  the plan is wrong — split the file's concerns or serialize the tasks.
- An agent that discovers it needs a file outside its lane stops and reports,
  instead of quietly expanding scope.

## Additional contracts for parallel work

- **No destructive git.** Parallel workers never run `stash`, `reset --hard`,
  or `checkout --` on shared state. The orchestrator makes a checkpoint commit
  before fanning out, so recovery is always possible.
- **Commits name their paths.** In a repo with concurrent sessions, commit
  with explicit pathspecs (or verify `git diff --cached --stat` first) so one
  session cannot sweep another session's staged files into its commit.

## Why

Agent drift is rarely malicious and always expensive: a helpful model fixes
"one more thing" three directories away, and the diff becomes unreviewable.
Ownership lists turn that into a mechanical check — reviewers verify the diff
stayed inside the declared paths before reading a single line of logic.
