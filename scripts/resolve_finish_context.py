#!/usr/bin/env python3
"""Resolve the branch, base, and optional plan used by the finishing skill."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path


def slug_tokens(value: str) -> set[str]:
    return {token for token in value.replace('_', '-').replace('/', '-').split('-') if token}

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()

def plan_slug(path: Path) -> str | None:
    for line in path.read_text(encoding='utf-8').splitlines()[:20]:
        if line.startswith('slug:'): return line.split(':', 1)[1].strip()
    return None

def resolve(root: Path, branch: str | None = None, base: str | None = None) -> dict:
    branch = branch or git(root, 'branch', '--show-current')
    base = base or 'main'
    slug = branch.split('/', 1)[1] if '/' in branch else branch
    exact = root/'specs'/slug/'PLAN.md'
    candidates = sorted((root/'specs').glob('*/PLAN.md')) if (root/'specs').is_dir() else []
    match_reason = None
    if exact.is_file():
        plan = exact
        match_reason = 'exact-directory'
        ambiguous = False
    else:
        direct = [p for p in candidates if plan_slug(p) == slug or slug in p.parent.name]
        if len(direct) == 1:
            plan = direct[0]
            match_reason = 'direct-slug'
            ambiguous = False
        elif len(direct) > 1:
            plan = None
            ambiguous = True
        else:
            # A conventional branch type is normally noise, but it becomes useful evidence when
            # the plan slug explicitly names the same work type (for example refactor/*).
            branch_tokens = slug_tokens(branch)
            scored = [(len(branch_tokens & slug_tokens(plan_slug(p) or p.parent.name)), p) for p in candidates]
            best = max((score for score, _ in scored), default=0)
            matches = [p for score, p in scored if score == best and score >= 2]
            plan = matches[0] if len(matches) == 1 else None
            ambiguous = len(matches) > 1
            if plan:
                match_reason = f'token-overlap:{best}'
    lane = None
    if plan and (plan.parent/'SUMMARY.md').is_file():
        for line in (plan.parent/'SUMMARY.md').read_text(encoding='utf-8').splitlines():
            if line.startswith('Lane:'): lane=line.split(':',1)[1].strip(); break
    try:
        merge_base = git(root, 'merge-base', 'HEAD', base)
        changed_files = [line for line in git(root, 'diff', '--name-only', f'{merge_base}..HEAD').splitlines() if line]
    except subprocess.CalledProcessError:
        merge_base = None
        changed_files = []
    workflow_engine = any(
        path.startswith(('skills/', 'agents/', 'rules/'))
        and (path.endswith('.md') or '/subagents/' in path or '/prompts/' in path)
        for path in changed_files
    )
    plan_dir = str(plan.parent.relative_to(root)) if plan else None
    return {
        'branch': branch, 'base': base, 'merge_base': merge_base, 'slug': slug,
        'plan_dir': plan_dir, 'lane': lane, 'ambiguous_plan': ambiguous, 'plan_match_reason': match_reason,
        'changed_files': changed_files,
        'receipt_path': f'{plan_dir}/.review-receipt.json' if plan_dir else None,
        'context_propagation_audit_required': workflow_engine,
    }

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--root', type=Path, default=Path.cwd()); p.add_argument('--branch'); p.add_argument('--base'); args=p.parse_args()
    try: print(json.dumps(resolve(args.root.resolve(), args.branch, args.base), sort_keys=True))
    except (OSError, subprocess.CalledProcessError) as e: print(f'finish-context: {e}', file=sys.stderr); return 1
    return 0
if __name__ == '__main__': raise SystemExit(main())
