# HOTFIX-slim-20260828ee6cde3108fb: git hooks must not lock everyone out when pactkit is missing

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-20260828ee6cde3108fb |
| Status | Done |
| Priority | P1 |
| Release | 2.25.0 |

## Background

The git hooks written by `install_git_hook` / `install_pre_push_hook`
(`src/pactkit/commit_gate.py`) call `exec pactkit commit-gate`.  On a
machine without the pactkit binary on PATH (teammates, CI runners, docker
builds — the default state in Node.js teams that never install Python),
the shell exits 127 and git treats the failed hook as a block: **every
commit and push is locked out by a broken gate**, violating the R3
self-lock protection principle (a gate that cannot run must WARN and
allow, not masquerade as enforcement).

## Target

`src/pactkit/commit_gate.py` — `install_git_hook` (~:687) and
`install_pre_push_hook` (~:702): generated hook scripts gain a PATH probe
(`command -v pactkit`) that prints a WARN and exits 0 when the binary is
missing.  The chain-onto-existing-hook path gets the same probe.

## Fix

Prepend to both generated scripts:

```sh
command -v pactkit >/dev/null 2>&1 || {
  echo "[WARN] pactkit not on PATH — gate skipped (unavailable, not enforced)"
  exit 0
}
```

Verification: unit tests assert the probe is present in installed hook
scripts (`tests/unit/test_commit_gate.py`, `tests/unit/test_push_gate.py`).
