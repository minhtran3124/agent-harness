---
ticket: 411
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0063. Fake login: serve.sh turns the env vars into a served config file

## Context

python3 -m http.server serves static files and cannot read env vars, but the ticket wants a login form that reads VERIFY_USER and VERIFY_PASSWORD.

## Options

- serve.sh writes the two values into a generated file in a temp dir and then serves it, with the form comparing client side
- a small Python server instead of http.server
- hard-code a demo credential in the HTML

## Decision

serve.sh copies the static files to a temp dir, writes the env var values into a generated login-config.json there (never in the tracked tree), and runs python3 -m http.server from that dir; the form compares input to that file.

## Why

Keeps to the confirmed http.server recipe, keeps secrets out of tracked files, and stays a fake form for a fixture only.

## Consequences

The fixture needs both env vars set (serve.sh exits non-zero with a clear message when they are missing); the test sets dummy values.

## How to reverse

Replace serve.sh with a Python server; the config's startCommand changes with it.
