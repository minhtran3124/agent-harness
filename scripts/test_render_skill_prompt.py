import json, subprocess, sys
from pathlib import Path
SCRIPT=Path(__file__).with_name('render_skill_prompt.py')

def run(*args): return subprocess.run([sys.executable, str(SCRIPT), *map(str,args)], capture_output=True, text=True)

def test_composes_provenance_and_values(tmp_path):
    a=tmp_path/'shared.md'; b=tmp_path/'role.md'; values=tmp_path/'values.json'
    a.write_text('shared {{NAME}}'); b.write_text('role'); values.write_text(json.dumps({'NAME':'Ada'}))
    r=run('--fragment',a,'--fragment',b,'--values',values)
    assert r.returncode==0 and 'source:' in r.stdout and 'shared Ada' in r.stdout

def test_rejects_unresolved_or_missing_fragment(tmp_path):
    a=tmp_path/'a.md'; a.write_text('{{MISSING}}')
    assert run('--fragment',a).returncode==1
    assert run('--fragment',tmp_path/'missing.md').returncode==1

def test_live_required_policy_delivery_passes():
    root=SCRIPT.parent.parent
    r=run('--root',root,'--check-all')
    assert r.returncode==0, r.stderr


def test_check_all_rejects_invalid_correctness_config(tmp_path):
    root = tmp_path
    for rel in (
        'skills/subagent-driven-development/implementer-prompt.md',
        'skills/correctness-review/prompts/shared.md',
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Read auto-correct-scope.md')
    config = root / 'skills/correctness-review/review-config.json'
    config.write_text(json.dumps({'finder_angles': ['one'], 'default_threshold': 75, 'minimum_threshold': 60}))
    r = run('--root', root, '--check-all')
    assert r.returncode == 1
    assert 'finder-angle' in r.stderr
