#!/bin/sh
# Install Ann's git hooks into .git/hooks (local, not version-controlled).
# Safe to re-run; overwrites the existing pre-commit hook.

root=$(git rev-parse --show-toplevel) || exit 1
cp "$root/Ann/scripts/pre-commit" "$root/.git/hooks/pre-commit"
chmod +x "$root/.git/hooks/pre-commit"
echo "Installed Ann pre-commit hook -> $root/.git/hooks/pre-commit"
echo "It runs pytest only when Ann/ files are staged. Override with 'git commit --no-verify'."
