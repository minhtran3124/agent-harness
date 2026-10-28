from pathlib import Path
import re
import subprocess
import sys
import sys
PLUGIN_SCRIPTS = Path(__file__).resolve().parent.parent / 'plugins/harness/scripts'
sys.path.insert(0, str(PLUGIN_SCRIPTS))
import rebuild_solution_index as idx

def doc(path, body):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body)

def test_build_groups_sorts_and_uses_missing_marker(tmp_path):
    doc(tmp_path/'docs/solutions/a/old.md', '---\nproblem_type: bug\nconfirmed_at: 2026-01-01\n---\n')
    doc(tmp_path/'docs/solutions/a/new.md', '---\nproblem_type: knowledge\nseverity: critical\ntags: [x, y]\napplicable_when: now\nconfirmed_at: 2026-02-01\n---\n')
    text=idx.build(tmp_path)
    assert text.index('[new]') < text.index('[old]')
    assert '| — | — | — |' in text

def test_empty_index_is_stable(tmp_path):
    first=idx.build(tmp_path); second=idx.build(tmp_path)
    assert first == second and '0 total entries' in first

def test_root_solution_readme_is_retained_as_uncategorized(tmp_path):
    doc(tmp_path/'docs/solutions/README.md', '# Readme\n')
    assert '## —' in idx.build(tmp_path)

def test_dry_run_does_not_write_index(tmp_path):
    script = PLUGIN_SCRIPTS / 'rebuild_solution_index.py'
    result = subprocess.run([sys.executable, str(script), '--root', str(tmp_path), '--dry-run'], capture_output=True, text=True)
    assert result.returncode == 0 and '0 total entries' in result.stdout
    assert not (tmp_path/'docs/solutions/INDEX.md').exists()

def _check(tmp_path):
    script = PLUGIN_SCRIPTS / 'rebuild_solution_index.py'
    return subprocess.run([sys.executable, str(script), '--root', str(tmp_path), '--check'], capture_output=True, text=True)

def _write_index(tmp_path, text):
    doc(tmp_path/'docs/solutions/INDEX.md', text)

def test_check_ignores_last_updated_date(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\nconfirmed_at: 2026-01-01\n---\n')
    text = idx.build(tmp_path)
    _write_index(tmp_path, re.sub(r'Last updated: \d{4}-\d{2}-\d{2}', 'Last updated: 2000-01-01', text))
    assert _check(tmp_path).returncode == 0

def test_check_fails_when_entry_added(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\nconfirmed_at: 2026-01-01\n---\n')
    _write_index(tmp_path, idx.build(tmp_path))
    doc(tmp_path/'docs/solutions/a/y.md', '---\nproblem_type: bug\nconfirmed_at: 2026-02-01\n---\n')
    result = _check(tmp_path)
    assert result.returncode == 1 and 'INDEX.md is stale' in result.stderr

def test_check_fails_when_only_entry_count_edited(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\nconfirmed_at: 2026-01-01\n---\n')
    text = idx.build(tmp_path)
    assert '| 1 total entries' in text
    _write_index(tmp_path, text.replace('| 1 total entries', '| 2 total entries'))
    assert _check(tmp_path).returncode == 1
