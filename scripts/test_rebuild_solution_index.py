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

def test_build_sorts_and_uses_missing_marker_for_optional_fields(tmp_path):
    doc(tmp_path/'docs/solutions/a/old.md', '---\nproblem_type: bug\napplicable_when: always\nconfirmed_at: 2026-01-01\n---\n')
    doc(tmp_path/'docs/solutions/a/new.md', '---\nproblem_type: knowledge\nseverity: critical\ntags: [x, y]\napplicable_when: now\nconfirmed_at: 2026-02-01\n---\n')
    text=idx.build(tmp_path)
    assert text.index('[new]') < text.index('[old]')
    assert '| bug | — | — | always |' in text

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
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\napplicable_when: now\nconfirmed_at: 2026-01-01\n---\n')
    text = idx.build(tmp_path)
    _write_index(tmp_path, re.sub(r'Last updated: \d{4}-\d{2}-\d{2}', 'Last updated: 2000-01-01', text))
    assert _check(tmp_path).returncode == 0

def test_check_fails_when_entry_added(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\napplicable_when: now\nconfirmed_at: 2026-01-01\n---\n')
    _write_index(tmp_path, idx.build(tmp_path))
    doc(tmp_path/'docs/solutions/a/y.md', '---\nproblem_type: bug\napplicable_when: now\nconfirmed_at: 2026-02-01\n---\n')
    result = _check(tmp_path)
    assert result.returncode == 1 and 'INDEX.md is stale' in result.stderr

def test_check_fails_when_only_entry_count_edited(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\napplicable_when: now\nconfirmed_at: 2026-01-01\n---\n')
    text = idx.build(tmp_path)
    assert '| 1 total entries' in text
    _write_index(tmp_path, text.replace('| 1 total entries', '| 2 total entries'))
    assert _check(tmp_path).returncode == 1

def _stderr_lines(result):
    return result.stderr.strip().splitlines()

def test_check_fails_when_applicable_when_key_absent(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\n---\n')
    _write_index(tmp_path, idx.build(tmp_path))
    result = _check(tmp_path)
    assert result.returncode == 1 and 'solution-index: a/x.md is missing applicable_when' in result.stderr

def test_check_fails_when_applicable_when_empty_or_whitespace(tmp_path):
    doc(tmp_path/'docs/solutions/a/e.md', '---\napplicable_when:\n---\n')
    doc(tmp_path/'docs/solutions/a/w.md', '---\napplicable_when:   \n---\n')
    _write_index(tmp_path, idx.build(tmp_path))
    result = _check(tmp_path)
    assert result.returncode == 1
    assert 'a/e.md is missing applicable_when' in result.stderr and 'a/w.md is missing applicable_when' in result.stderr

def test_check_exempts_readme_and_critical_patterns(tmp_path):
    doc(tmp_path/'docs/solutions/README.md', '# Readme\n')
    doc(tmp_path/'docs/solutions/critical-patterns.md', '# Patterns\n')
    _write_index(tmp_path, idx.build(tmp_path))
    assert _check(tmp_path).returncode == 0
    assert '[README]' in idx.build(tmp_path)

def test_check_reports_missing_before_stale(tmp_path):
    doc(tmp_path/'docs/solutions/a/x.md', '---\nproblem_type: bug\n---\n')
    _write_index(tmp_path, 'stale\n')
    result = _check(tmp_path)
    lines = _stderr_lines(result)
    assert result.returncode == 1
    assert lines[0] == 'solution-index: a/x.md is missing applicable_when'
    assert lines[1] == 'solution-index: INDEX.md is stale'
