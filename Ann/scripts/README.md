# Ann developer scripts

## pre-commit hook

`pre-commit` runs Ann's pytest suite before a commit is created, but **only when
the commit stages files under `Ann/`**. Because this repository is a
multi-project mono-repo, commits to other projects skip the hook entirely.

### Install (one-time, local)

```sh
sh Ann/scripts/install-hooks.sh
```

This copies the hook into `.git/hooks/pre-commit` (git hooks live outside version
control, so each clone installs them once).

### Behaviour

- No Ann files staged → hook exits immediately, commit proceeds.
- Ann files staged → `pytest Ann/current/tests` runs; a failure aborts the commit.
- Override a blocked commit with `git commit --no-verify`.

> Note: the self-updater (`updater.py`) already re-runs pytest in `staging/`
> before swapping a new version in. This hook is a lighter, earlier local gate —
> it catches breakage at commit time rather than at update time.
