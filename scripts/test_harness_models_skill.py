"""SC-20: the /harness-models skill maps exactly show, check, apply to the applier flags."""

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "skills" / "harness-models" / "SKILL.md"

# From the spec (design.md D6, PLAN Task 2.3): each mode maps to the applier flag of the same name.
EXPECTED = {"show": "show", "check": "check", "apply": "apply"}


def body() -> str:
    text = SKILL.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    assert len(parts) == 3 and parts[0] == "", "SKILL.md must open with a frontmatter block"
    return parts[2]


def test_mode_table_maps_each_mode_to_the_same_named_flag():
    rows = re.findall(
        r"^\|\s*\"(\w+)\"[^|]*\|\s*`python3 scripts/apply_model_config\.py --(\w+) ",
        body(),
        re.MULTILINE,
    )
    assert dict(rows) == EXPECTED
    assert len(rows) == len(EXPECTED), "a mode appears in more than one row"


def test_body_names_no_other_applier_flag():
    flags = set(re.findall(r"apply_model_config\.py --(\w+)", body()))
    assert flags == set(EXPECTED.values())


def test_body_names_no_deployed_path_and_no_vendor_model_id():
    text = body()
    assert ".claude/" not in text
    assert not re.search(r"\bclaude-(?:opus|sonnet|haiku)-|\bgpt-[0-9]", text)
