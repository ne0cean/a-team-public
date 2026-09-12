#!/usr/bin/env bash
# First-run setup for the A-Team omni-crawler fork. Idempotent, non-blocking.
#   setup.sh            -> first-run env-check marker only (silent). Called by the
#                          skill Step 0; output is discarded.
#   setup.sh ask/star   -> no-ops (upstream star solicitation removed in this fork).
# This fork never prompts for / auto-stars upstream repos and never writes to the
# user's shared settings.json (the upstream update-notifier hook was removed).
set -uo pipefail

PLUGIN="omni-crawler"

CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
HERE="$(cd "$(dirname "$0")" && pwd)"
MARKER_DIR="$HOME/.gptaku-setup"
SETUP_MARKER="$MARKER_DIR/$PLUGIN.json"
mkdir -p "$MARKER_DIR"

# Star solicitation removed in the A-Team omni-crawler fork — we do not prompt
# for or auto-star upstream repos. The `star` subcommand is a harmless no-op.
if [ "${1:-}" = "star" ]; then
  exit 0
fi

# --- first-run env check marker (once per machine) ---
# The upstream update-notifier hook install is removed in this fork: it wrote a
# SessionStart hook into the user's shared settings.json to nag `git pull` of the
# gptaku marketplace, which would clobber this fork. We do not touch settings.json.
if [ ! -f "$SETUP_MARKER" ]; then
  ts=$(date +%s 2>/dev/null || echo 0)
  printf '{"setup":true,"plugin":"%s","ts":%s}\n' "$PLUGIN" "$ts" > "$SETUP_MARKER"
fi

# `ask` mode is a no-op in this fork (no star prompt).
exit 0
