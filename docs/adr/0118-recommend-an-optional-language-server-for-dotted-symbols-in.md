---
ticket: 523
stage: design
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-30
---

# 0118. Recommend an optional language server for dotted symbols in ground-check.sh, with grep + WARN fallback

## Context

ground-check.sh check_symbol accepts a dotted symbol when each segment appears somewhere on the ref, so wrong pairs pass, and runs one git grep per segment. Spike #523 measured four methods on a Python and a TS fixture (28 claims each: 15 exists, 6 missing, 7 wrong-pair). Pinned versions: pyright 1.1.414 (pip), typescript-language-server 6.0.2 with typescript 5.9.3 (npm; typescript 7.0.2 ships no tsserver.js, so it was not usable), graphify 0.9.97 (pip package graphifyy), code-review-graph 2.3.9 (pip). Results (ok = correct/total; FF = false fail on exists; FP = false pass on missing or wrong-pair): baseline py and ts: exists 15/15, missing 6/6, wrong-pair 0/7 (FP 7 each), cold 0.17/0.14 s, repeat 0.16/0.14 s. Language server py and ts: 15/15, 6/6, 7/7, FF 0, FP 0, cold 0.56/0.76 s, repeat 0.62/0.76 s. graphify py and ts: exists 5/15 and 2/15 (FF 10 and 13), missing 6/6, wrong-pair 7/7, cold 0.27/0.26 s, repeat 0.27/0.23 s. code-review-graph py and ts: exists 5/15 and 1/15 (FF 10 and 14), missing 6/6, wrong-pair 7/7, cold 0.48/0.46 s, repeat 0.18/0.18 s. The graph tools score full marks on wrong-pair only because they reject almost every dotted claim: they do not resolve global names (json.dumps, JSON.stringify), aliased imports (import x as y, import * as ns), module constants, class attributes or instance variables. Every false pass and false fail was checked against the fixture: the labels were confirmed independently (Python by evaluating each claim at runtime, TS by compiling each claim with tsc), and the baseline false passes are claims whose two names both appear in the fixture sources. Install size: pyright venv 64 MB, typescript-language-server plus typescript 26 MB, graphify 219 MB, code-review-graph 348 MB. Timings are for tiny fixtures and exclude install; they show relative start cost only. Headless: all four ran from a script through subprocess with stdio only, no editor (LSP over stdio; graphify update and code-review-graph build as CLIs, the graph read from graph.json or SQLite). The session note that /reload-plugins found 0 plugin LSP servers was not reproduced: the servers were started directly by path, so whether a workflow agent can reach the Claude Code plugin LSP is untested and stays a finding for the follow-up. Data egress: pyright and typescript-language-server read code locally over stdio (the pip pyright wrapper uses nodeenv and npm, so it may fetch pyright from the npm registry on first run; no source is sent). graphify update is a local AST pass with no LLM call; graphify extract is the full extraction and sends code to an LLM backend selected by API key (Anthropic, OpenAI, Gemini, Kimi, DeepSeek endpoints are in its source), and the --code-only flag named in the ticket does not exist in 0.9.97. code-review-graph build is local SQLite; embeddings are off by default and the cloud providers (openai, google, minimax, voyage) may transmit source-derived text. No packet capture was done; these egress statements come from the CLI help and source, and the tool output stayed untrusted throughout. One limit of the result: a language server needs a scope to resolve the qualifier, so the runner appends the claim to its context file; a research brief claim has no context file, so the follow-up must define one (for example the file the brief cites, or a probe file per import scope).

Codegraph 1.6.2 was added after the first measurement. With the same (container, member) rule as the other graph tools it scored exists 5/15 py and 3/15 ts (FF 10 and 12), missing 6/6, wrong-pair 7/7, cold 0.46 s. An alias-aware row also reads the import aliases and `instantiates` edges of the context file: exists 10/15 on both languages (FF 5 and 5), missing 6/6, wrong-pair 7/7 (FP 0), cold 0.49 and 0.52 s. Four of the five Python misses and all five TS misses are stdlib or language globals, which the index does not hold; the fifth Python miss is a class attribute (`Cart.CURRENCY`) that the index lacks. The language server and graphify rows were not re-run with this row: their numbers are from the first measurement.

## Options

- Keep grep only (current baseline): fast, no install, but accepts every wrong pair
- Use a language server (pyright, typescript-language-server) for dotted symbols, optional, grep fallback with WARN
- Use graphify or code-review-graph: rejected, they reject most valid dotted claims (FF 10 to 14 of 15)
- Use codegraph: rejected for this check, it rejects valid claims (FF 10 to 12 of 15, or 5 of 15 with alias reading added in the runner), and the alias reading is a per-language regex this repo would have to maintain
- Make a language server a required plugin dependency: out of scope and heavier than needed

## Decision

ground-check.sh should check a dotted symbol with the language server for the file language (pyright for Python, typescript-language-server for TS/JS) when the binary is on PATH, and report any claim the server cannot resolve as FAIL. When the binary is missing or does not start, it falls back to today's grep check and prints WARN naming the missing tool and that wrong pairs are not caught. The server is never a required dependency of the plugin. graphify, code-review-graph and codegraph are not used for dotted symbols.

## Why

Only the language server rejected all 7 wrong pairs per language (FP 0) and accepted all 15 real claims (FF 0). The graph tools lose 10 to 14 of 15 real claims because they do not resolve globals, aliases, constants or instances. The cost is about 0.6 to 0.8 s per run against 0.15 s for grep, and 26 to 64 MB of optional install, with no code leaving the machine.

## Consequences

A follow-up ticket changes ground-check.sh and ship.js (out of scope here) and must decide which context file scopes each claim, and how to start the server once per run so cold time is not paid per symbol. CI and machines without the tools keep the grep behaviour plus a WARN. The runner and fixtures stay in the repo, so the measurement can be repeated.

## How to reverse

Do not implement the follow-up, or have it drop the language-server branch; ground-check.sh is unchanged by this ticket and the runner and fixtures can be deleted without side effects.
