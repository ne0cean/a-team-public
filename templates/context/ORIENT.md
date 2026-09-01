# ORIENT — How This Project Actually Runs

> Keep this file under ~15 lines. It answers one question: "an agent just
> opened this repo — what must it know before running anything?"
> If the project ships to multiple surfaces (web + mobile + desktop), say
> which one is the source of truth.

## Surfaces

- Primary surface: <web | mobile PWA | desktop app | CLI | library>
- Source of truth when surfaces disagree: <which one>

## Run

- Dev: `<command>` (serves at `<url>`)
- Test: `<command>`
- Build: `<command>`

## Deploy

- Target: <platform / host>
- Command or trigger: `<command, or "CI on push to main">`
- Anything that must NEVER be deployed directly: <e.g. "never deploy from a feature branch">
