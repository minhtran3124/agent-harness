#!/bin/sh
# Report whether a directory is a regular checkout, linked worktree, or submodule.
# Usage: detect-isolation.sh [directory]
set -u

target=${1:-.}
root=$(git -C "$target" rev-parse --show-toplevel 2>/dev/null) || {
  printf '%s\n' 'error: not a git worktree' >&2
  exit 2
}
git_dir=$(git -C "$target" rev-parse --absolute-git-dir)
common_dir=$(git -C "$target" rev-parse --git-common-dir)
case "$common_dir" in
  /*) ;;
  *) common_dir=$(cd "$root/$common_dir" && pwd -P) ;;
esac
superproject=$(git -C "$target" rev-parse --show-superproject-working-tree 2>/dev/null || true)

if [ -n "$superproject" ]; then
  mode=submodule
  isolated=false
elif [ "$git_dir" != "$common_dir" ]; then
  mode=linked-worktree
  isolated=true
else
  mode=main-worktree
  isolated=false
fi

branch=$(git -C "$target" symbolic-ref --quiet --short HEAD 2>/dev/null || printf '%s' detached)
printf '{"root":"%s","branch":"%s","mode":"%s","isolated":%s}\n' \
  "$root" "$branch" "$mode" "$isolated"
