# Generate the HTML tour

`generate` builds one standalone HTML file, `<skill directory>/rendered/tour.html`, with a card for
every OpenWiki page. The wiki is the only source for its text. Source code is used only by the
claim checks.

## Steps

1. Plan: run `python3 <skill directory>/scripts/build_tour.py plan`. It prints the sections and
   their pages as JSON. If it exits 2 (no wiki), say so and stop.
2. Dispatch one agent per section, all in one message, with `model` set to `haiku`. Give each
   agent the prompt below, filled in with the section id, its page list, and the output path
   `.harness-state/onboarding/pages/<section id>.json`.
3. Build: run `python3 <skill directory>/scripts/build_tour.py build`. It checks every record
   against its wiki page and writes the tour only when every check passes.
4. If it prints `error:` lines, dispatch again only the sections those lines name. Add the
   error text to each new prompt under "Fix these". Run step 3 again. After two rounds, stop and
   report what still fails.
5. Report the pages written, the claim count (ok of total), and the file path. Do not paste the HTML.
6. Serve: run `python3 <skill directory>/scripts/build_tour.py serve` in the background, and give
   the newcomer the URL it prints. Stop it when they are done.
7. Publish with the Artifact tool only when the newcomer asks. Otherwise the file stays local.

## Agent prompt

You write the tour text for one section of an OpenWiki. The wiki is the only source. Do not read
source code, tests, docs, or specs. Read only the pages listed below, under `openwiki/`.

Section id: `<section id>`
Pages (paths relative to `openwiki/`):
`<page list>`
Output file: `<output path>`

For each page, write one record:

- `page`: the path, exactly as listed.
- `why`: one or two plain sentences on why this part exists, in the page's own terms. Under 30 words.
- `breaks`: 2 to 4 items, each `{"t": "<what breaks, in plain words>", "src": "<heading>"}`.
  `src` is the exact text of a heading in that page, without the `#` marks. Copy it exactly.
  Every page needs at least one break.
- `tests`: 0 to 4 items, each `{"cmd": "<command or path>", "what": "<a few words>", "src": "<heading>"}`.
  `cmd` must appear word for word in the page. Invent nothing.

Rules:

- Use only facts the pages state. If a page does not say it, leave it out.
- Keep sentences short and plain. Paraphrase. Never copy a sentence longer than 30 words.
- Write only this JSON to the output file: `{"section": "<section id>", "pages": [ ... ]}`.
- Your reply is one line: the output path and the number of pages written.

Fix these (present only on a second round): `<error lines for this section>`

## Why the checks are strict

`build_tour.py build` rejects any record whose `src` is not a heading of its page, and any `cmd`
that is not in its page. This keeps the tour traceable to the wiki. It does not prove that a
sentence is true. Use the verify counts for that, and the page's source link for the wording.
