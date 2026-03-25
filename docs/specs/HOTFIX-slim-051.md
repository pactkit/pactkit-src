# HOTFIX-slim-051: CI template respects pactkit.yaml ci.install_cmd override

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-051 |
| Status | Done |

## Background

`_build_github_workflow()` in `deployer.py:1001` hardcodes `ci_prof['install_cmd']` from `CI_PROFILES`. It ignores `ci_config` (from `pactkit.yaml`), so `pactkit update` reverts any custom CI install commands (e.g. `pip install -e ".[multilang]"`) every time.

## Fix

Target: `src/pactkit/generators/deployer.py:1001` — change `ci_prof['install_cmd']` to `ci_config.get('install_cmd', ci_prof['install_cmd'])`, allowing `pactkit.yaml` `ci.install_cmd` to override the default.

Also update pactkit's own `.claude/pactkit.yaml` to set the custom install_cmd.
