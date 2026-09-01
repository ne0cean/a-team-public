#!/usr/bin/env node
// Minimal event logger. Appends one JSON line per call to
// .context/analytics.jsonl at the repo root (created on first use).
//
// Usage:  node scripts/log-event.mjs <event> [key=value ...]
// Example: node scripts/log-event.mjs command_start name=vibe
//
// Commands in .claude/commands call this for usage telemetry. It is safe to
// no-op (delete the file and calls still exit 0 in most shells via `|| true`),
// but keeping it lets you measure which workflows you actually use.

import { appendFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';

const [event, ...pairs] = process.argv.slice(2);
if (!event) {
  console.error('usage: log-event.mjs <event> [key=value ...]');
  process.exit(0); // never fail a calling workflow over telemetry
}

const record = { event, ts: new Date().toISOString() };
for (const pair of pairs) {
  const eq = pair.indexOf('=');
  if (eq > 0) record[pair.slice(0, eq)] = pair.slice(eq + 1);
}

try {
  const out = join(process.cwd(), '.context', 'analytics.jsonl');
  mkdirSync(dirname(out), { recursive: true });
  appendFileSync(out, JSON.stringify(record) + '\n');
} catch {
  // telemetry must never break a workflow
}
