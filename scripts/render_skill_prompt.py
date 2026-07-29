#!/usr/bin/env python3
"""Compose isolated-subagent prompts from explicit fragments with provenance."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

def read(path: Path) -> str:
    if not path.is_file(): raise ValueError(f'missing fragment: {path}')
    return path.read_text(encoding='utf-8').strip()

def render(fragments: list[Path], values: dict[str, str]) -> str:
    parts=[]
    for path in fragments:
        text=read(path)
        for key,value in values.items(): text=text.replace('{{'+key+'}}', value)
        if '{{' in text or '}}' in text: raise ValueError(f'unresolved placeholder in {path}')
        parts.append(f'<!-- source: {path.as_posix()} -->\n{text}')
    return '\n\n'.join(parts)+'\n'

def check_all(root: Path) -> list[str]:
    errors=[]
    required={
      root/'skills/subagent-driven-development/implementer-prompt.md': 'auto-correct-scope.md',
      root/'skills/correctness-review/prompts/shared.md': 'auto-correct-scope.md',
    }
    for path, token in required.items():
        if not path.is_file() or token not in path.read_text(encoding='utf-8'):
            errors.append(f'missing required policy delivery: {path.relative_to(root)} -> {token}')
    config = root / 'skills/correctness-review/review-config.json'
    try:
        data = json.loads(read(config))
        angles = data.get('finder_angles')
        if not isinstance(angles, list) or len(set(angles)) != 6:
            errors.append('invalid correctness finder-angle config')
        if data.get('default_threshold') != 75 or data.get('minimum_threshold') != 60:
            errors.append('invalid correctness threshold config')
    except (ValueError, json.JSONDecodeError):
        errors.append('missing or unreadable correctness review config')
    return errors

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--fragment', type=Path, action='append', default=[]); p.add_argument('--values', type=Path); p.add_argument('--check-all', action='store_true'); p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent); args=p.parse_args()
    try:
        if args.check_all:
            errors=check_all(args.root.resolve())
            if errors:
                for error in errors: print(f'prompt-compose: {error}', file=sys.stderr)
                return 1
            print('prompt-compose: all contracts present'); return 0
        if not args.fragment: p.error('provide --fragment or --check-all')
        values=json.loads(args.values.read_text()) if args.values else {}
        if not isinstance(values, dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in values.items()): raise ValueError('--values must be a JSON object of strings')
        print(render(args.fragment, values), end=''); return 0
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f'prompt-compose: {e}', file=sys.stderr); return 1
if __name__ == '__main__': raise SystemExit(main())
