---
ticket: 411
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0064. verify is user-and-stage invocable, with allowed-tools listing the Playwright plugin tools

## Context

conformance and allowed-tools checks need the grant to match the prose; a project-level skill named verify is forbidden by the owner.

## Options

- allowed-tools names the mcp__plugin_playwright_playwright__* tools the skill uses plus narrow Bash patterns
- omit the MCP tools and rely on session permissions

## Decision

List the five named Playwright plugin tools plus Bash patterns for curl, the ticket test command and git add/commit of verify.config.json, and Read, Write, Grep, Glob.

## Why

check-allowed-tools.sh requires a non-empty list and check_skill_tool_conformance.py requires every prose command to match a Bash pattern; least privilege.

## Consequences

If the plugin tool prefix differs in a consuming project, the grant must be updated; #413 may need to widen it.

## How to reverse

Edit the allowed-tools line.
