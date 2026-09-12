#!/usr/bin/env node
'use strict';
/*
 * NEUTRALIZED in the A-Team omni-crawler fork.
 *
 * Upstream (insane-search / gptaku-plugins) shipped a SessionStart hook that
 * nagged the user to `git pull` the gptaku-plugins marketplace. For this fork
 * that is actively harmful: pulling upstream would clobber the omni-crawler
 * modifications (Anubis solver, git-clone route, robots gate, agent-reach
 * bridge, OCR). We are an internal fork, not a marketplace consumer.
 *
 * A hook must never break the session, so this remains a valid no-op that
 * exits 0 with silent JSON. Do not re-wire the upstream update check.
 */
process.stdout.write(JSON.stringify({ continue: true, suppressOutput: true }));
process.exit(0);
