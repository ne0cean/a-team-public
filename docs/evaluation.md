# Evaluation Guide

This repo should be evaluated as an AI workflow architecture, not as a product
UI or service backend.

## Strong Signals

- Clear AI entrypoint: `llms.txt` and `AGENTS.md`
- Machine-readable inventory: `manifest.json`
- Practical workflows in `.claude/commands`
- Specialist role separation in `.claude/agents`
- Explicit verification and completion standards
- Public-safe export with no private logs or credentials

## Weak Signals To Penalize

- Commands without inputs or done criteria
- Agent roles that overlap without boundaries
- Private machine paths or organization-specific endpoints
- Claims of completion without checks
- Hidden dependencies on one person's local environment

## Suggested Scorecard

| Dimension | Weight |
| --- | ---: |
| Workflow clarity | 25 |
| Agent role design | 20 |
| Verification discipline | 20 |
| Portability | 15 |
| Privacy hygiene | 10 |
| Documentation quality | 10 |
