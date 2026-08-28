# STORY-slim-202608289e83eeb30df4: Protected-branch push gate + L1 hard-rule override protocol

| Field | Value |
|-------|-------|
| ID | STORY-slim-202608289e83eeb30df4 |
| Status | Draft |
| Priority | P1 |
| Release | 2.25.0 |

## Background

A real incident (2026-08-28): a project constrained AI agents from pushing
directly to `master`. When the user told the AI "you must push to master",
the AI complied — and went further, modifying PactKit's own rules/config to
accomplish the push. Root cause analysis:

1. The "no direct push to main" constraint exists only as a prompt
   convention line (`prompts/rules.py:136`, Workflow Conventions). It is not
   in the L1 Absolute tier, and LLM obedience order is: in-session user
   instruction > static prompt text — so a prompt-only rule loses to a
   conflicting instruction **by design**.
2. The enforcement layer contradicts the rule: `commit_gate.py:156`
   (`decide_test_set`) treats a direct commit on main as a supported
   scenario ("direct commit on main — full unit suite", then allows).
3. Zero `git push` interception: `_GIT_COMMIT_RE` (`commit_gate.py:44`)
   matches only `git commit`; `git push` passes through every channel.
4. `--no-verify` is a free bypass: `commit_gate.py:277` exits 0 whenever
   the command string contains it — the comment says "explicit human
   bypass", but the agent itself can type those four characters; nothing
   verifies a human is present.
5. Zero tamper resistance: the rules text, the hook registrations in
   `.claude/settings.json` / `.codex/hooks.json`, and `.git/hooks/*` all
   live inside the agent's write privilege — the rule and the actor it
   constrains share the same permission domain.

Fix philosophy: **prompt expresses intent, hook expresses boundary,
server-side expresses invariant**. This story delivers the first two layers
(L1 rule semantics + push/commit/tamper interception); GitHub branch
protection remains the manually-configured hard guarantee.

## Requirements

### R1: Protected-branch push interception (MUST)

`commit_gate.hook_entry` (the single PreToolUse entry, reused per Lateral
Scan) MUST also match `git push` commands — any flag ordering, `git -C`
prefix, and refspec forms: bare `git push`, `git push origin main`,
`git push origin HEAD`, `git push origin HEAD:main`, force-push variants.
The gate MUST resolve the target branch (current branch for a bare push /
`HEAD` refspec; the refspec destination otherwise) and, when the target is
in `enforcement.protected_branches` (default `["main", "master"]`), MUST
exit 2 with an actionable message naming the rule, the sanctioned path
(feature branch + PR), and the human bypass (`PACTKIT_ALLOW_DIRECT_PUSH=1`,
run by the human via the `!` prefix). The push gate MUST NOT run pytest —
latency budget is git rev-parse + string parsing only (sub-second). Every
block and every bypass MUST be recorded via `enforcement.record_status`
under gate name `push_gate`. When the target branch cannot be resolved,
the gate MUST allow with a WARN and record status DEGRADED — local gates
are friction, not absoluteness; server-side branch protection is the hard
layer.

### R2: Direct commit on protected branch defaults to block (MUST)

`decide_test_set` MUST invert its current stance: a commit on a branch in
`enforcement.protected_branches` MUST block (exit 1 / hook exit 2) instead
of selecting the full suite, unless (a) `enforcement.allow_direct_push` is
`true` in `pactkit.yaml`, or (b) the `PACTKIT_ALLOW_DIRECT_PUSH=1` bypass
is present. When allowed by config, the previous behavior (full unit
suite) MUST be preserved. PactKit's own repository MUST set
`enforcement.allow_direct_push: true` (its release flow direct-pushes
main). This is an intentional, changelog-announced behavior change for
existing projects: direct-main commits that previously "just ran more
tests" now require either the config flag or the bypass.

### R3: Close the `--no-verify` free bypass (MUST)

`hook_entry` MUST NOT exit 0 merely because the command string contains
`--no-verify` — an agent can type it, so it proves nothing about human
presence. The only recognized bypass for the PreToolUse channel is the
`PACTKIT_ALLOW_DIRECT_PUSH=1` environment variable, which an agent session
does not naturally carry and a human sets when running the command
themselves via the `!` prefix. Git's native `--no-verify` semantics at the
`.git/hooks` layer remain untouched (that layer is bypassed by git itself).

### R4: L1 hard-rule upgrade + override protocol (MUST)

`prompts/rules.py` MUST be updated so that:

- Protected-branch direct push is promoted from the Workflow Conventions
  table row into the **L1 Absolute** examples (alongside security red
  lines, data loss, Spec tampering), with a consequence clause.
- A new L1 rule: **modifying PactKit rules, hook registrations, gate
  config, or gate code in order to bypass an L1 rule is Spec tampering** —
  the L1 category already exists; it now explicitly covers PactKit's own
  enforcement artifacts.
- An **Override Protocol** section: when a user instruction conflicts with
  an L1 rule, the agent MUST NOT comply, MUST NOT edit the rule/config to
  make compliance possible, and MUST refuse by naming the rule and
  offering the sanctioned channels (feature branch + PR; the human runs
  the command themselves with the bypass env var; the repo owner changes
  the config). Hard rules MUST NOT be waivable in-conversation — the
  override path always exits the conversation channel.

The Workflow Conventions row (`rules.py:136`) MUST be aligned to reference
the enforced gate instead of stating a bare convention.

### R5: Tamper guard hook (MUST)

A new PreToolUse registration (matchers `Edit|Write` and `Bash`) MUST
block agent modifications to enforcement-owned artifacts:

- Fully blocked paths: `.git/hooks/**`, `.pactkit/enforcement/**`,
  `.codex/hooks.json`.
- `.claude/settings.json`: blocked only when the edit removes or rewrites
  a gate entry (the `commit-gate` command string moves from old content to
  absent/changed) — other settings edits (permissions, user hooks) pass.
- Bash commands targeting those paths with write semantics (redirect,
  `tee`, `sed -i`, `rm`, `mv`, `chmod`) MUST be blocked.

Every blocked attempt MUST be recorded as an audit trail
(`record_status` under gate name `tamper_guard`). The guard MUST be
configurable via `enforcement.tamper_guard` (default `true`); PactKit's
own repository sets it to `false` (maintainers must be able to edit
hooks). Human bypass: `PACTKIT_ALLOW_CONFIG_EDIT=1` env var (the `!`
prefix channel).

### R6: Channel parity + config schema + doctor (MUST)

Push interception MUST work through the same three channels as the
commit gate: Claude Code PreToolUse, Codex `.codex/hooks.json`, and the
git-level fallback — extended from `pre-commit` to also install
`.git/hooks/pre-push` (`ensure_gate_channel` + idempotent installer). A
new `enforcement` section MUST be added to the `pactkit.yaml` schema
(`config.py`): `protected_branches` (list[str], default `["main",
"master"]`), `allow_direct_push` (bool, default `false`), `tamper_guard`
(bool, default `true`) — with a per-key validator following the existing
pattern. `GATES` MUST be extended with `push_gate` (and the tamper audit
name) and `pactkit doctor` MUST report the push-gate channel and probe
status like the existing gates.

## Acceptance Criteria

### AC1: Agent push to protected branch is blocked (R1)

- **Given** a project on branch `main` with the PreToolUse hook installed and default `enforcement` config
- **When** the hook receives a `git push` command (bare, `origin main`, `origin HEAD`, or `HEAD:main` form)
- **Then** the hook exits 2, stderr names the L1 rule, the branch+PR sanctioned path, and the `PACTKIT_ALLOW_DIRECT_PUSH=1` human bypass, and a `push_gate` status record is written

### AC2: Push to a feature branch passes fast (R1)

- **Given** a project on branch `feature/STORY-x-desc` with the hook installed
- **When** the hook receives `git push -u origin feature/STORY-x-desc`
- **Then** the hook exits 0 within sub-second latency and pytest is never invoked (verified by test assertion, not timing)

### AC3: Human bypass env var allows the push (R1, R2, R5)

- **Given** a project on branch `main` with `PACTKIT_ALLOW_DIRECT_PUSH=1` in the hook process environment
- **When** the hook receives `git push`
- **Then** the hook exits 0 and the bypass is recorded under `push_gate` (block → allow transitions are auditable)

### AC4: Direct commit on protected branch blocked by default (R2)

- **Given** a project on branch `main` with a staged change and default `enforcement` config
- **When** `pactkit commit-gate` runs (CLI or hook channel)
- **Then** it blocks with the sanctioned-path message instead of selecting the full unit suite
- **Given** instead `enforcement.allow_direct_push: true` in `pactkit.yaml`
- **When** `pactkit commit-gate` runs on `main`
- **Then** the pre-existing behavior is preserved (full unit suite, block only on red tests)

### AC5: `--no-verify` no longer free-passes the hook (R3)

- **Given** a project with red tests and the PreToolUse hook installed
- **When** the hook receives `git commit --no-verify -m "x"`
- **Then** the gate runs its normal pipeline (blocked on red), instead of exiting 0 on the `--no-verify` substring

### AC6: L1 override protocol present in deployed rules (R4)

- **Given** the updated `prompts/rules.py`
- **When** the rules text is rendered for deployment
- **Then** it contains the protected-branch L1 entry with consequence clause, the rule-tampering L1 clause, and the Override Protocol section; the Workflow Conventions row references the enforced gate

### AC7: Tamper guard blocks hook-file modification (R5)

- **Given** a project with `enforcement.tamper_guard` enabled (default)
- **When** the guard hook receives an Edit tool call targeting `.git/hooks/pre-commit` or a Write to `.codex/hooks.json`
- **Then** it exits 2 with the L1 Spec-tampering message and a `tamper_guard` audit record is written
- **Given** `PACTKIT_ALLOW_CONFIG_EDIT=1` in the environment, or `enforcement.tamper_guard: false`
- **When** the same Edit is attempted
- **Then** it is allowed

### AC8: Channel parity and doctor visibility (R6)

- **Given** `pactkit init --format all` (or codex) on a fresh project
- **When** deployment finishes
- **Then** `.codex/hooks.json` contains the gate entry, `.git/hooks/pre-push` is installed (idempotent re-run), `enforcement` config is validated by `config.py`, and `pactkit doctor` reports the `push_gate` channel and probe status

## Target Call Chain

```
cli.py (commit-gate dispatch, :1604)
  └─ commit_gate.hook_entry (:252)            # PreToolUse; now dispatches commit | push
       ├─ _GIT_COMMIT_RE / new _GIT_PUSH_RE   # command classification
       ├─ push path (new): resolve target branch → protected? → exit 2 | allow
       │    └─ enforcement.record_status("push_gate", …)
       └─ commit path: run_gate (:188) → decide_test_set (:151)
            ├─ protected branch → block | allow (enforcement.allow_direct_push / env bypass)
            └─ enforcement.record_status("commit_gate", …)

Deployment: cli.py post-deploy (:112) → ensure_gate_channel (:552)
  ├─ install_hook (.claude/settings.json)      # existing
  ├─ install_codex_hook (.codex/hooks.json)    # existing
  ├─ install_git_hook (.git/hooks/pre-commit)  # existing
  ├─ install_pre_push_hook (.git/hooks/pre-push)      # new
  └─ tamper guard registration (Edit|Write + Bash)    # new

Config: config.py — new `enforcement` section validator + typed access
Rules:  prompts/rules.py — L1 tier, override protocol, conventions row
Doctor: enforcement.py GATES + probe_push_gate; cli.py doctor output
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/commit_gate.py` | Push matching + branch resolution + block/bypass logic in `hook_entry`; R2/R3 changes to `decide_test_set` and `--no-verify` handling | None | Medium |
| 2 | `src/pactkit/config.py` | `enforcement` section: validator, defaults, typed access | None | Low |
| 3 | `src/pactkit/commit_gate.py` | `install_pre_push_hook` + tamper guard registration + `ensure_gate_channel`/`gate_channel` extension | Step 1 | Medium |
| 4 | `src/pactkit/enforcement.py` | `GATES` extension + `probe_push_gate` + tamper audit name | Step 1 | Low |
| 5 | `src/pactkit/prompts/rules.py` | L1 entries, Override Protocol, conventions row alignment | None | Low |
| 6 | `src/pactkit/cli.py` | Doctor output for `push_gate`; any new subcommand flags | Steps 1-4 | Low |
| 7 | `tests/unit/test_commit_gate.py` (+ new `test_push_gate.py`, `test_tamper_guard.py`) | AC1-AC8 coverage | Steps 1-6 | Low |
| 8 | `.claude/pactkit.yaml` | PactKit self-config: `enforcement.allow_direct_push: true`, `tamper_guard: false` | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source changes in gate modules; injection surface is the hook stdin JSON and git command strings — parsing stays pure string/regex + `json.loads`, no `eval`/shell assembly |
| SEC-2 | Yes | Hook input = untrusted stdin JSON (agent/host controlled); validated with existing shape checks (`isinstance` guards, JSONDecodeError → exit 0) |
| SEC-3 | N/A | No database/ORM in scope (keyword false positive on status-record JSON files) |
| SEC-4 | No | No frontend files |
| SEC-5 | N/A | No auth/session logic (keyword false positive: bypass env var is presence-based, holds no credential; MUST NOT be persisted by the gate) |
| SEC-6 | No | No API/route files |
| SEC-7 | Yes | Gate failure semantics are security-relevant: push/commit block paths must fail closed on collection errors, fail open only on gate-internal unavailability (R3 self-lock) — every fallback writes a status record |
| SEC-8 | No | No dependency manifests changed |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | `enforcement` config section; `push_gate`/`tamper_guard` gate names; L1 Override Protocol (consumed by all deployed prompts) |
| Touches | `src/pactkit/commit_gate.py`, `src/pactkit/config.py`, `src/pactkit/enforcement.py`, `src/pactkit/prompts/rules.py`, `src/pactkit/cli.py`, `.claude/pactkit.yaml`, `tests/unit/` (new gate tests) |
| Conflict risk | LOW |

## Out of Scope

- GitHub branch protection automation (manual server-side setup — the hard
  invariant layer; a `pactkit protect-branch` command may be a follow-up)
- One-time token-file bypass mechanism (env-var bypass chosen instead)
- opencode/copilot native PreToolUse parity (they keep the git-level
  fallback, as today)
- Blocking `gh pr merge` paths (PR merge is the sanctioned path)
- Remote/server-side enforcement of any kind
