from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import resolve_finish_context as ctx

def plan(root, slug):
    p=root/'specs'/slug/'PLAN.md'; p.parent.mkdir(parents=True); p.write_text(f'---\nslug: {slug}\n---\n')
    (p.parent/'SUMMARY.md').write_text('Lane: normal\n'); return p

def test_exact_branch_slug_wins(tmp_path, monkeypatch):
    plan(tmp_path, 'thing'); plan(tmp_path, 'other-thing')
    monkeypatch.setattr(ctx, 'git', lambda *_: 'abc123')
    data=ctx.resolve(tmp_path, 'feat/thing', 'main')
    assert data['plan_dir']=='specs/thing' and data['lane']=='normal' and not data['ambiguous_plan']

def test_ambiguous_fallback_never_guesses(tmp_path, monkeypatch):
    plan(tmp_path, 'gh-1-thing'); plan(tmp_path, 'gh-2-thing')
    monkeypatch.setattr(ctx, 'git', lambda *_: 'abc123')
    data=ctx.resolve(tmp_path, 'feat/thing', 'main')
    assert data['plan_dir'] is None and data['ambiguous_plan']

def test_context_reports_changed_files_receipt_and_audit_need(tmp_path, monkeypatch):
    plan(tmp_path, 'thing')
    def fake_git(_, *args):
        if args[:2] == ('merge-base', 'HEAD'):
            return 'base123'
        if args[:2] == ('diff', '--name-only'):
            return 'skills/demo/SKILL.md\ndocs/readme.md'
        return 'abc123'
    monkeypatch.setattr(ctx, 'git', fake_git)
    data = ctx.resolve(tmp_path, 'feat/thing', 'main')
    assert data['changed_files'] == ['skills/demo/SKILL.md', 'docs/readme.md']
    assert data['receipt_path'] == 'specs/thing/.review-receipt.json'
    assert data['context_propagation_audit_required'] is True


def test_unique_two_token_branch_plan_overlap_resolves_with_reason(tmp_path, monkeypatch):
    plan(tmp_path, 'skill-prompt-refactor')
    plan(tmp_path, 'unrelated-plan')
    monkeypatch.setattr(ctx, 'git', lambda *_: 'abc123')
    data = ctx.resolve(tmp_path, 'refactor/skill-prompt-surface', 'main')
    assert data['plan_dir'] == 'specs/skill-prompt-refactor'
    assert data['plan_match_reason'] == 'token-overlap:3'


def test_two_equal_token_overlap_candidates_are_ambiguous(tmp_path, monkeypatch):
    plan(tmp_path, 'skill-prompt-refactor')
    plan(tmp_path, 'prompt-skill-refactor')
    monkeypatch.setattr(ctx, 'git', lambda *_: 'abc123')
    data = ctx.resolve(tmp_path, 'refactor/skill-prompt-surface', 'main')
    assert data['plan_dir'] is None and data['ambiguous_plan']
