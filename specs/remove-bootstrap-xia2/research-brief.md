# Research — Removing `bootstrap-xia2`: what it does, what breaks, how to adapt without it

Status: research/thinking only (no change made). Requested 2026-07-17: "remove bootstrap-xia2 — we don't need to run/install this skill; find another way to adapt without it."

All facts below verified against the tree on 2026-07-17.

---

## 1. What bootstrap-xia2 actually is

A **370-line companion skill** to `xia2`, user-triggered (never in the auto workflow chain). It is a **one-time setup helper**: scan a repo, auto-detect signals, and produce draft config for human review. Two modes — **Init** (no PROJECT.md yet) and **Update** (refresh, writes `.proposed`, never overwrites).

It produces / scaffolds **four kinds of output**:

| Output | Consumer | Hard dependency? |
|---|---|---|
| `xia2/PROJECT.md` | `xia2` PROJECT-CONFIG-GATE | **YES** — xia2 halts without it (SKILL.md:28, :86) |
| `agents/PROJECT.md` | execution agents (`coding.md`, `test-runner.md`) | soft — agents fall back to inline |
| `rules/architecture.md` + `guidelines.md` | agents at planning/review | soft — generic skeleton works |
| Scaffolds `specs/`, `docs/solutions/`, `agent-memory/` from 6 bundled templates | the whole workflow | one-time — once created, never needed again |

The **bulk of the 370 lines (99–278) is detection heuristics** — prose instructions for an LLM to grep/scan for high-blast files, manifests, contracts, auth surfaces, entry points, etc. This is the automation the skill exists to provide.

## 2. The single hard dependency, and its escape hatch already exists

`xia2` cannot classify without `xia2/PROJECT.md` — its gate **halts** if the file is missing/incomplete/stale. But the gate itself already documents **two** ways to satisfy it (SKILL.md:28):

> "instruct the user to bootstrap one via `/bootstrap-xia2` (auto-scan helper) **or by copying `PROJECT.template.md`**."

So **the manual-template path is already a first-class, documented alternative.** `xia2/PROJECT.template.md` exists (11 required/optional sections with inline guidance). Removing bootstrap-xia2 does **not** break xia2 — it removes the *automated draft*, leaving the *manual fill* path the gate already advertises.

## 3. What actually breaks if you just `git rm` the skill

Not xia2 (manual path survives). The real couplings:

1. **6 bundled structural templates die with the skill** (`skills/bootstrap-xia2/templates/*`) — specs-README, specs-STATE, docs-solutions-{README,INDEX,critical-patterns}, agent-memory-README. **For THIS repo: harmless** — all 6 destinations already exist. **For a NEW consuming repo: this is the scaffolding capability**; deleting it with no replacement means a fresh install has no way to create those files. → If removed, these templates must **relocate** (e.g. to `templates/`) or the manual onboarding path must point at them.
2. **Doc references** that would go stale (doc-truth lint scans some): `rules/architecture.md:20,26`, `rules/guidelines.md:6`, `xia2/SKILL.md:28,86,238`, `agents/README.md`, `agents/PROJECT.template.md`, `README.md:83`, `harness-manifest.json:94` (inventory — check_manifest may care), CLAUDE.md.
3. **The `.proposed` refresh mechanism** — bootstrap Update is what writes `PROJECT.md.proposed` / `agents/PROJECT.md.proposed`. We just promoted `agents/PROJECT.md.proposed` in Phase 2 wave 3; without bootstrap there is no automated drift-refresh (manual edit only).
4. **`bootstrap-xia2` in the resync guard** (README:83) — the installer's "bootstrap-generated files kept" logic references it by name.

## 4. The dogfooding signal (both directions — be fair)

**Against keeping it:** This meta-repo's own `xia2/PROJECT.md` is **the unfilled generic template** ("reusable template — regenerate it per project"), not a filled config for this repo. In ~2 months of the harness's life, bootstrap-xia2's *primary output was never completed for the repo that ships it* — the `research-harness-req-assessment.md` flagged exactly this (Q3 gap: xia2 loses its main signal source). That is weak evidence the automation earns 370 lines **here**, and it is consistent with the over-engineering review's theme (the harness improving itself faster than it is used) and with the wave-3 decision to cut 3 of 5 stack profiles.

**For keeping it:** bootstrap-xia2's audience is **consuming repos**, not this meta-repo. A team installing the harness into a large existing codebase gets an auto-scanned draft of 8 required PROJECT.md sections instead of hand-filling them cold — that is real onboarding value for the exact audience the harness targets. The meta-repo's unfilled PROJECT.md is a *dogfooding gap*, not proof the tool is useless. Removing it makes first-run onboarding materially harder for consumers.

**The deciding question is therefore not technical — it is:** *Is this harness genuinely distributed to consumers who onboard cold, or is it effectively single-user tooling?* The same criterion that decided the wave-3 stacks cut (owner chose "cut" → leaning pragmatic/single-user). Consistency points toward removal **provided the manual path stays intact**.

## 5. Options to adapt without the skill

| # | Option | What it costs / preserves | Fit |
|---|---|---|---|
| **A** | **Delete the skill; keep `PROJECT.template.md` + relocate the 6 structural templates to `templates/`; update xia2's gate wording to say "copy the template and fill it" (drop the bootstrap mention).** | −370 lines + the heuristics. Onboarding becomes: copy template, fill 8 sections by hand. Scaffolding survives via relocated templates + a short README step. | **Recommended if single-user / low-onboarding.** Cleanest; honours "we don't need to run this skill." |
| **B** | **Replace the skill with a deterministic `scripts/bootstrap-project.sh`** — a real scan that emits a draft PROJECT.md. | Moves heuristics from prose→code (testable). But the skill's core value ("which files are *really* high-blast") is an explicit **human-judgment** call the prose defers — a script can only draft the mechanical 60%. ~150 lines of bash + tests to maintain. | Only if onboarding automation is genuinely wanted but you dislike a prose-skill. |
| **C** | **Fold lazy init into `xia2` itself** — on first run with no PROJECT.md, xia2 scans + drafts instead of halting. | No separate skill, no cold halt. But bloats xia2 and mixes config-generation into classification (the two were deliberately split — "universal logic here, project mappings there"). | Rejected — undoes xia2's portability design. |
| **D** | **Remove xia2's PROJECT.md dependency entirely** — xia2 classifies from inline defaults + on-the-fly detection, no config file. | Eliminates the whole bootstrap *need*, not just the skill. Biggest simplification. But loses per-project signal precision (the High-Blast/Shared-Contract lists that make classification accurate) — xia2 becomes generic. Large redesign of xia2. | The deepest cut; separate, larger decision. Worth a spike, out of scope for "remove bootstrap." |

## 6. Recommendation

**Option A**, contingent on the deciding question in §4. It directly grants the user's intent ("don't need to run this skill"), removes 370 lines of maintenance-heavy heuristic prose, and — crucially — **loses no capability that this repo still needs**, because (a) xia2's manual template path already exists and is documented, and (b) all 6 scaffold destinations already exist here; the templates only need to survive for *future* consumers, which relocating them to `templates/` handles.

**Hard constraints for the removal (so it doesn't become an unverified-premise cut):**
1. Relocate the 6 structural templates out of the skill dir before deleting it — or the scaffolding capability dies silently for consumers.
2. Rewrite xia2's two gate mentions (SKILL.md:28, :86) + the `- /bootstrap-xia2` reference (:238) to the manual path; update `rules/architecture.md`, `rules/guidelines.md`, `agents/README.md`, `README.md`, `harness-manifest.json`, CLAUDE.md.
3. Decide the `agents/PROJECT.md` / `PROJECT.md` **`.proposed` refresh** story — with bootstrap gone, drift-refresh is manual; note it or accept it.
4. Keep `xia2/PROJECT.template.md` (it becomes the sole onboarding artifact) and consider pulling the best detection hints from the skill into the template's section comments as a fill-in checklist, so the human doesn't lose the "what to look for" guidance the heuristics encoded.

**If the answer to §4 is "yes, real consumers onboard cold":** keep bootstrap-xia2, but it should still shrink — the stack-profile rendering half now only serves fastapi + _skeleton (post wave-3), so steps 7/§6 of the skill can lose the multi-profile machinery.

## 7. Open question for the owner

The whole analysis pivots on **§4's deciding question.** State the harness's intended distribution and the removal path is determined:
- **Single-user / few cold onboards →** Option A (remove; recommended).
- **Genuine multi-consumer product →** keep + shrink, or Option B.
