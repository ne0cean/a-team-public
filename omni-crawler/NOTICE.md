# NOTICE — A-Team Omni-Crawler

This project is a fork of **insane-search v0.9.1** (MIT © 2026 fivetaku),
modified by A-Team. The upstream MIT license is retained verbatim in `LICENSE`
and applies to all inherited code.

A-Team modifications ("Omni-Crawler") add the following, each in
`skills/insane-search/engine/`:

- **Anubis PoW solver** (`anubis.py`) — solves SHA-256 proof-of-work
  interstitials for a single legitimate reader (capped difficulty, one solve per
  host per run; no proxy/distributed solving).
- **git-clone-first route** (`git_route.py`) — clones a repo once (shallow,
  blob:none) instead of scraping HTML commit-by-commit.
- **robots.txt politeness gate** (`robots.py`) — honours robots.txt for the
  generic HTML grid by default.
- **agent-reach bridge** (`platform_bridge.py`, `phase0._github`) — routes
  platform surfaces (e.g. GitHub issues/PRs/gists) through installed backend CLIs.
- **OCR enrichment** (`ocr.py`) — optional Gemini OCR of images in fetched
  content (opt-in, key-gated).
- **Video transcript** (`video.py`) — optional extraction of public captions
  from yt-dlp caption tracks (opt-in `INSANE_TRANSCRIPT`; public captions only).

## Roadmap (deliberately deferred)

- **SSO video transcription** — `yt-dlp --cookies-from-browser` + Whisper for
  login-gated videos. Deferred: reading the user's browser cookies for arbitrary
  sites is a privacy hazard and Whisper is a heavy dependency. If added, it must
  be a separate explicit opt-in, never on by default.

## Third-party references

- **Anubis** — proof-of-work anti-scraper gate, MIT © Xe Iaso / Techaro.
  Source: https://github.com/TecharoHQ/anubis
  Only the *client-side* PoW handshake is implemented, to let a single reader
  through; nothing from the Anubis server is copied.
- **"creepy-crawlies" essay** by Konstantin Ryabitsev (kernel.org), which
  motivated the git-clone-first + politeness design:
  https://people.kernel.org/monsieuricon/creepy-crawlies
- **Gemini API** (OCR backend) — https://ai.google.dev/ — used only when the
  operator supplies their own `GEMINI_API_KEY`.

## Safety scope (all A-Team additions)

No residential/mobile proxy swarms, no multi-IP ban evasion, no distributed
mass-targeting, no multi-node clone amplification. These additions let a single
polite client read public content; they are deliberately not a scraping fleet.
