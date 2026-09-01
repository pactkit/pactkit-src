# HOTFIX-slim-20260830bbb5bc219d35: gate CLI syntax mismatch + push-gate cross-repo blind spot

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-20260830bbb5bc219d35 |
| Status | Done |
| Priority | P1 |
| Release | 2.25.1 |

## Background

Two defects surfaced during the 2.25.0 release run (post-tag, so they
ship in 2.25.1):

1. **auth-gate teaches a CLI form that does not exist.** The block
   message (and the L1 Override Protocol prompt text, and
   critical-rules.md on the user's machine) instructs
   `pactkit gate authorize <scope>` — but the `gate` parser accepts only
   the bare positional `pactkit gate <scope>`. The documented form fails
   with "unrecognized arguments". Unit tests call `auth_gate.authorize()`
   directly, so the CLI layer was never exercised. Every internal user
   hits this on their first external-effect command.
2. **push-gate evaluates the wrong repository for cross-repo commands.**
   `cd ~/other-repo && git push` is judged against the SESSION cwd's
   enforcement config (payload `cwd`), not the target repo's — observed
   live when the plugin-repo push was allowed by pactkit's own
   `allow_direct_push: true` although the plugin repo has no config.

## Fix

1. `cli.py`: `gate` accepts both `pactkit gate authorize <scope>` and
   `pactkit gate <scope>` (positional `scope` becomes `nargs="*"`; an
   `authorize` keyword is normalized away). Help text documents both.
   All existing message/prompt text becomes correct as-is.
2. `commit_gate.py`: `_command_root()` resolves the last `cd <dir>`
   prefix target in the command (absolute, or relative to the payload
   root; non-dirs ignored) and `hook_entry` evaluates gates against that
   root — a `cd`-prefixed command is judged by the repo it operates on.

Verification: focused unit tests for both behaviors + full suite +
regenerated `gate.txt` help golden. Push to main only; no release, no
version bump, no adapter/plugin/site sync (deferred to 2.25.1).
