# HOTFIX-slim-099: Fix version mismatch guard to use semantic comparison

## Background
`check_version_mismatch()` in `guards.py` uses string `!=` to compare yaml version vs installed version. This gives a misleading "Run `pactkit update` to sync" message even when yaml version is **newer** than installed — in which case the user should upgrade pactkit, not downgrade the yaml.

## Target
- **File**: `src/pactkit/guards.py`
- **Function**: `check_version_mismatch()` (line 71-85)

## Fix
- Use `packaging.version.Version` for semantic comparison
- yaml > installed → suggest `pipx upgrade pactkit`
- yaml < installed → suggest `pactkit update`
- equal → no warning (existing behavior)
