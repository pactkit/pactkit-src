# Spec STORY-014: Release v1.1.3 — sync CHANGELOG, plugin, and PyPI
- **Release**: 1.1.3

## Context
BUG-003/004/005 were fixed and committed to `main` but the following distribution artifacts are out of sync:
1. **CHANGELOG.md** — missing `[1.1.2]` entry (BUG-001/002) and BUG-003/004/005 entries
2. **Plugin repo** (`pactkit/claude-code-plugin`) — still ships buggy `visualize.py` and `board.py`
3. **PyPI** — v1.1.2 does not include BUG-003/004/005 fixes

README.md and pactkit.dev website require no changes (overview-level docs unaffected by internal bug fixes).

## Requirements
- MUST update CHANGELOG.md with `[1.1.2]` section (BUG-001, BUG-002) and `[1.1.3]` section (BUG-003, BUG-004, BUG-005).
- MUST bump version to `1.1.3` in `pyproject.toml`, `__init__.py`, and `pactkit.yaml`.
- MUST regenerate plugin output and push to `pactkit/claude-code-plugin`.
- MUST build and publish `pactkit==1.1.3` to PyPI.
- MUST create git tag `v1.1.3`.
- SHOULD verify deployed plugin artifacts contain all 3 bug fixes.
- SHOULD verify PyPI package installs correctly and `pactkit version` returns `1.1.3`.

## Acceptance Criteria

### Scenario 1: CHANGELOG is complete
- **Given** the CHANGELOG.md file
- **When** a reader looks at it
- **Then** sections `[1.1.2]` and `[1.1.3]` exist with all bug fix entries

### Scenario 2: Version numbers are consistent
- **Given** `pyproject.toml`, `__init__.py`, and `pactkit.yaml`
- **When** compared
- **Then** all three show version `1.1.3`

### Scenario 3: Plugin repo is synced
- **Given** the `pactkit/claude-code-plugin` repo
- **When** inspecting `visualize.py` and `board.py`
- **Then** both contain the BUG-003 and BUG-005 fixes

### Scenario 4: PyPI package is current
- **Given** `pip install pactkit==1.1.3`
- **When** running `pactkit version`
- **Then** output shows `1.1.3`

## Design
1. Update CHANGELOG.md
2. Bump version (3 files)
3. Commit + tag `v1.1.3`
4. `pactkit init --format marketplace -t /tmp/marketplace` → push to plugin repo
5. `python3 -m build && twine upload dist/*` → publish to PyPI

## Target Call Chain
No code changes — this is a release engineering story.
