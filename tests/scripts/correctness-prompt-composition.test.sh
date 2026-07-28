#!/bin/bash
source "$(dirname "$0")/../lib.sh"
CONFIG="skills/correctness-review/review-config.json"
FINDER="skills/correctness-review/correctness-reviewer-prompt.md"
SCORER="skills/correctness-review/correctness-scorer-prompt.md"

t "review config declares six unique finder angles"
count=$(python3 -c 'import json; print(len(set(json.load(open("'"$ROOT/$CONFIG"'"))["finder_angles"])))')
if [ "$count" -eq 6 ]; then pass; else fail "angle count=$count"; fi

t "finder prompt contains every configured angle"
missing=""
while IFS= read -r angle; do grep -q "\`$angle\`" "$ROOT/$FINDER" || missing="$missing $angle"; done < <(python3 -c 'import json; print("\n".join(json.load(open("'"$ROOT/$CONFIG"'"))["finder_angles"]))')
if [ -z "$missing" ]; then pass; else fail "missing:$missing"; fi

t "every configured angle composes with the shared child contract"
bad=""
while IFS= read -r angle; do
  out=$(python3 "$ROOT/scripts/render_skill_prompt.py" --fragment "$ROOT/skills/correctness-review/prompts/shared.md" --fragment "$ROOT/skills/correctness-review/prompts/angles/$angle.md" 2>&1) || bad="$bad $angle:$out"
done < <(python3 -c 'import json; print("\n".join(json.load(open("'"$ROOT/$CONFIG"'"))["finder_angles"]))')
if [ -z "$bad" ]; then pass; else fail "composition failed:$bad"; fi

t "scorer prompt matches threshold anchors and bounds"
python3 - "$ROOT/$CONFIG" "$ROOT/$SCORER" <<'PY'
import json, sys
config = json.load(open(sys.argv[1]))
text = open(sys.argv[2]).read()
for score in config["score_anchors"]:
    assert f"**{score}**" in text or f"<{ '|'.join(map(str, config['score_anchors'])) }>" in text
assert f"default threshold is **{config['default_threshold']}**" in text
assert f"floor is {config['minimum_threshold']}" in text
PY
if [ "$?" -eq 0 ]; then pass; else fail "scorer/config drift"; fi

finish
