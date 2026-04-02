# STORY-slim-072: PactGuard PDCA Integration

| Field | Value |
|-------|-------|
| ID | STORY-slim-072 |
| Status | Done |
| Priority | P1 |
| Release | 3.0.0 |

## Background

Both Anthropic and OpenAI's harness engineering articles converge on one principle: **constraints must be mechanically enforced, not prompt-dependent**. OpenAI uses custom linters + structural tests; Anthropic uses an independent Evaluator agent. Both reject "asking the model to follow the rules" as a reliable strategy.

PactKit already enforces one mechanical gate: `spec_linter.py` blocks `/project-act` at Phase 0.5 if the Spec has errors. PactGuard (sibling project, v1.0.x) provides deterministic pattern rules + LLM-judgment review rules for code compliance.

The natural integration: PactKit as the **Harness** (flow control), PactGuard as the **Linter** (constraint enforcement). This story adds PactGuard as an **optional, config-gated** Check Phase extension:
- Check Phase 4.5: Run `pactguard check` on changed files (mode configurable: pattern/all)

The integration is **off by default** — controlled by `check.pactguard.enabled` in `pactkit.yaml`. When disabled or PactGuard not installed, the phase is silently skipped (no Verdict row). This avoids blocking Act/Done flows and keeps the feature non-intrusive until the user explicitly opts in.

## Requirements

### R1: Check Phase Gate — PactGuard Scan (MUST)

The Check command playbook MUST include a new `Phase 4.5: PactGuard Compliance Scan` step:
1. Read `check.pactguard.enabled` from `pactkit.yaml` — if `false` (default): **silently skip** (no Verdict row, no log)
2. If enabled: check if `pactguard` CLI is available (`which pactguard`) — if not found: silently skip
3. Run `pactguard check --mode {check.pactguard.mode} -r {check.pactguard.ruleset} <changed_files> --json-output`
4. Parse JSON output — include in Phase 5 Verdict table: `PactGuard | PASS/WARN/FAIL | N pattern violations, M review suggestions`
5. If `check.pactguard.blocking: true` and violations found: contribute to FAIL verdict

Act and Done playbooks MUST NOT be modified.

### R2: Configuration in pactkit.yaml (MUST)

The `check` section in `pactkit.yaml` MUST support a new `pactguard` sub-section:
```yaml
check:
  security_checklist: true          # existing
  security_scope_override: none     # existing
  pactguard:                        # NEW
    enabled: false                  # default OFF
    mode: "all"                     # pattern | all
    ruleset: ""                     # path to ruleset YAML (empty = PactGuard default)
    blocking: false                 # if true, violations → FAIL verdict
```

Defaults: `enabled: false`, `mode: "all"`, `ruleset: ""`, `blocking: false`.

### R3: Playbook Template Variables (MUST)

New template variables MUST be added to `_render_prompt()` var_map:
- `{PACTGUARD_ENABLED}` — resolves to `true`/`false` from `check.pactguard.enabled`
- `{PACTGUARD_MODE}` — resolves to `pattern`/`all` from `check.pactguard.mode`
- `{PACTGUARD_RULESET}` — resolves to the configured ruleset path (empty string if not set)

### R4: Graceful Degradation (MUST)

When `check.pactguard.enabled: true` but dependencies unavailable:
- PactGuard not installed → silently skip (no Verdict row)
- Ruleset file not found → silently skip (no Verdict row)
- PactGuard exits with error → report error in Verdict row as WARN, do not block

## Acceptance Criteria

### AC1: Check Phase Runs PactGuard When Enabled (R1)

- **Given** PactGuard is installed and `pactkit.yaml` has `check.pactguard.enabled: true`
- **When** `/project-check` runs Phase 4.5
- **Then** agent runs `pactguard check --mode {mode}` on changed files and includes results in Phase 5 Verdict

### AC2: Silently Skips When Disabled (R1)

- **Given** `pactkit.yaml` has `check.pactguard.enabled: false` (or key absent)
- **When** `/project-check` runs
- **Then** Phase 4.5 is silently skipped — no log, no Verdict row for PactGuard

### AC3: Silently Skips When Not Installed (R4)

- **Given** `check.pactguard.enabled: true` but PactGuard CLI is NOT installed
- **When** `/project-check` runs Phase 4.5
- **Then** phase is silently skipped — no Verdict row

### AC4: Config Defaults Are OFF (R2)

- **Given** a fresh `pactkit.yaml` with no `check.pactguard` section
- **When** `load_config()` merges defaults
- **Then** `config["check"]["pactguard"]["enabled"]` is `False`

### AC5: Template Variables Render (R3)

- **Given** `pactkit.yaml` has `check.pactguard.enabled: true` and `check.pactguard.ruleset: "rulesets/owasp.yaml"`
- **When** `pactkit deploy` renders the Check playbook
- **Then** the deployed `project-check.md` contains `{PACTGUARD_ENABLED}` resolved to `true`

### AC6: Blocking Mode Contributes to FAIL (R1)

- **Given** `check.pactguard.blocking: true` and PactGuard reports 3 violations
- **When** Phase 4.5 completes
- **Then** the violations contribute to a FAIL verdict in Phase 5

## Target Call Chain

```
/project-check
  → Phase 4: E2E [existing]
  → Phase 4.5: PactGuard Compliance Scan (NEW)
    → read config["check"]["pactguard"]["enabled"]
    → if false (default): silently skip → Phase 4.7
    → which pactguard → if not found: silently skip → Phase 4.7
    → pactguard check --mode {mode} -r {ruleset} --json-output <changed_files>
    → parse JSON → format Verdict row (PASS/WARN/FAIL)
    → if blocking and violations: contribute FAIL to verdict
  → Phase 4.7: Observability Scan [STORY-slim-073]
  → Phase 5: Verdict [existing, conditionally extended with PactGuard row]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_config.py` | TDD: tests for `check.pactguard` config parsing, defaults, validation | None | Low |
| 2 | `src/pactkit/config.py` | Add `pactguard` sub-section to `check` defaults, deep merge, validation | None | Low |
| 3 | `src/pactkit/prompts/commands.py` | Add Phase 4.5 block to Check template (config-gated, silent skip) | Step 2 | Medium |
| 4 | `src/pactkit/generators/deployer.py` | Add `{PACTGUARD_*}` variables to `_render_prompt()` var_map | Step 2 | Low |
| 5 | `tests/e2e/cli/test_cli_e2e.py` | E2E: deploy with pactguard config → verify rendered Check playbook | Step 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | MUST | Ruleset path from YAML must be validated (no absolute paths outside project) |
| SEC-2 (Auth) | N/A | No auth changes |
| SEC-3 (Injection) | MUST | PactGuard CLI invocation in playbook template — path must not allow injection |
| SEC-4 (Secrets) | N/A | No credential handling |
| SEC-5 (CORS) | N/A | CLI-only |
| SEC-6 (Path Traversal) | MUST | Ruleset path must resolve within project or known config dirs |
| SEC-7 (DoS) | N/A | Bounded by changed file count |
| SEC-8 (Dependencies) | N/A | PactGuard is optional; no hard dependency added |

## Out of Scope

- PactGuard auto-install (user must install `pactguard` separately)
- Custom rule authoring from within PactKit (PactGuard's own concern)
- PactGuard review rule LLM execution (PactGuard Phase 2)
- Act/Done phase integration (all PactGuard logic is in Check only)
- Activation friction reduction (doctor hints, auto-enable) — deferred to dogfood validation
- PactGuard results in Memory MCP (future: store compliance history)
