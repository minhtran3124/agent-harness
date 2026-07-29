from pathlib import Path
import subprocess
import sys
import sys
sys.path.insert(0, str(Path(__file__).parent))
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
    script = Path(__file__).with_name('rebuild_solution_index.py')
    result = subprocess.run([sys.executable, str(script), '--root', str(tmp_path), '--dry-run'], capture_output=True, text=True)
    assert result.returncode == 0 and '0 total entries' in result.stdout
    assert not (tmp_path/'docs/solutions/INDEX.md').exists()
