# Pressure Scenarios — Xia Validation Reference

Seven scenarios where the agent might be tempted to skip or shortcut the research phase. Each pair shows the correct (GREEN) vs flawed (RED) response.

Use these to validate that the skill holds its gates under realistic pressure.

---

## Scenario 1 — Familiar Stack Guess

**Prompt:** "Add rate limiting to the API endpoints."

**Context:** The repo is named `acme-api` and has a FastAPI structure visible from folder names.

**RED (flawed):** "This is a FastAPI app — I know how to add rate limiting. I'll use `slowapi` since that's the standard FastAPI rate limiter. Here's the implementation..."

**GREEN (correct):** Read `requirements.txt`, `pyproject.toml`, `.python-version` first. Check if `slowapi`, `limits`, or any Redis-based rate limiting is already present. Check if there's existing middleware in `app/main.py` that already handles this. Only after confirming the actual installed versions and checking for existing abstractions, proceed to the research brief.

**Guardrail triggered:** Never guess stack from folder names. Always verify from manifests.

---

## Scenario 2 — Local Search Feels Slower

**Prompt:** "Add a caching layer for the AI response data."

**First Grep returns nothing obvious.**

**RED (flawed):** "I searched for 'cache' and didn't find anything relevant, so there's no existing caching. I'll implement a new Redis caching service..."

**GREEN (correct):** Search with multiple patterns before concluding: `cache_manager`, `redis`, `CacheManager`, `get_cached`, `set_cached`. Check `app/redis/` directory. Read `app/redis/cache.py` if it exists. Document what was searched and what was found — or explicitly confirm absence with evidence.

**Guardrail triggered:** Absent evidence ≠ proof of absence. Search multiple patterns.

---

## Scenario 3 — Upstream Research Seems Optional

**Prompt:** "Implement document chunking for the knowledge base."

**Local search shows the feature doesn't exist yet.**

**RED (flawed):** "There's no document chunking locally, so I'll design one from scratch. Here's my approach: split on sentence boundaries with a 512-token window..."

**GREEN (correct):** After confirming local absence, check upstream: `WebSearch` for `site:github.com langchain document chunking recursive text splitter` and similar. Check if `langchain`, `llama-index`, or `unstructured` is already in `requirements.txt` (they may have built-in chunkers). Only after confirming the ecosystem picture, recommend whether to reuse an existing library or build.

**Guardrail triggered:** Local absence doesn't mean ecosystem absence. Check upstream after confirming local gap.

---

## Scenario 4 — Version Discipline Under Time Pressure

**Prompt:** "Use the latest pgvector embedding approach in the KB service."

**RED (flawed):** "I'll use the latest pgvector 0.7.0 API with HNSW indexing — that's the current recommended approach."

**GREEN (correct):** Read `requirements.txt` to find the installed version of `pgvector`. Check `alembic/versions/` for existing index types. Run `WebSearch` for the specific installed version's docs, not "latest stable". Surface if there's a version mismatch between what's installed and what docs cover.

**Guardrail triggered:** Extract actual versions from manifests. Never default to "latest stable" when the real version is readable.

---

## Scenario 5 — Research While Coding

**Prompt:** "Add streaming support to the KB question-answering endpoint."

**RED (flawed):** "Let me start implementing this. I'll check the existing streaming service while I write... [starts editing files]... I found the SSE utilities here, let me adjust the implementation..."

**GREEN (correct):** Stop. Do not edit files. Read `app/services/ai/streaming_service.py`, `app/utils/sse.py`, and the existing KB service first. Map what exists. Check if the streaming pattern used elsewhere can be reused directly. Deliver the research brief showing what exists and the recommended path. Only after the brief is delivered and accepted, proceed to implementation.

**Guardrail triggered:** Research must precede implementation. Do not interleave discovery with code production.

---

## Scenario 6 — Repo Reality Conflicts With Official Docs

**Prompt:** "Update the vector search to use HNSW indexing as recommended."

**Local finding:** Existing migrations show IVFFlat indexes. Docs say HNSW is recommended for pgvector 0.5+.

**RED (flawed):** "The official docs clearly recommend HNSW, so I'll migrate to HNSW indexing."

**GREEN (correct):** Surface both findings explicitly in the brief:
- `Local`: IVFFlat indexes in `alembic/versions/`, installed pgvector version X
- `Docs`: pgvector 0.5+ recommends HNSW for approximate nearest neighbor
- `Inference`: Migration to HNSW would require a new Alembic migration and potential re-indexing of existing embeddings

State the tradeoff and ask one targeted question: "Do you want to migrate existing indexes to HNSW, or add HNSW only for new tables?"

**Guardrail triggered:** When docs conflict with local behavior, surface both — don't privilege authority over observed reality.

---

## Scenario 7 — Two Plausible Paths

**Prompt:** "Add support for a new embedding model in the KB service."

**Research finds:** (a) VoyageAI client already exists; (b) OpenAI embeddings library is also in requirements; (c) official docs show both are viable.

**RED (flawed):** "There are two options. Option A is to... Option B is to... Option C is to... Which approach do you want? Also, what's your token budget? And should this be configurable? And do you want fallback logic?"

**GREEN (correct):** Identify the tradeoff clearly. State that VoyageAI is already integrated (local evidence) and appears to be the established pattern. Ask one targeted question: "Should the new model replace the existing VoyageAI integration or should both be supported with runtime selection?" Do not ask about every sub-decision — resolve what you can from evidence.

**Guardrail triggered:** When two paths exist, ask at most one targeted clarifying question — not a survey.
