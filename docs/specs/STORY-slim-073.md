# STORY-slim-073: Agent Observability Layer

| Field | Value |
|-------|-------|
| ID | STORY-slim-073 |
| Status | Done |
| Priority | P1 |
| Release | 3.0.0 |

## Background

OpenAI's Harness Engineering article emphasizes making the application **readable to agents**: they integrated Chrome DevTools MCP for DOM snapshots, screenshots, and console inspection; built a local observability stack with LogQL/PromQL for logs and metrics; and enabled git worktree per agent instance for isolation.

PactKit's `/project-check` already conditionally integrates Playwright MCP and Chrome DevTools MCP (rule `06-mcp-integration.md`), but the current integration is raw — the agent gets unstructured tool outputs (DOM snapshots, console logs, network requests) and must interpret them ad-hoc.

This story adds a structured **observability protocol** to the Check command: a standardized way to collect, format, and present runtime signals (console errors, network failures, performance metrics) as agent-consumable structured data. The feature is **off by default** — controlled by `check.observe.enabled` in `pactkit.yaml`. When disabled or MCP tools unavailable, the phase is silently skipped (no Verdict row). This keeps the feature non-intrusive until the user explicitly opts in.

## Requirements

### R1: Observation Collection Protocol (MUST)

A new `pactkit observe` CLI subcommand MUST collect runtime signals from available MCP tools and format them as structured JSON:

```json
{
  "timestamp": "2026-03-31T10:00:00Z",
  "source": "chrome-devtools",
  "signals": {
    "console_errors": [{"level": "error", "message": "...", "source": "app.js:42"}],
    "network_failures": [{"url": "...", "status": 500, "method": "POST"}],
    "performance": {"lcp_ms": 1200, "fcp_ms": 400, "cls": 0.05}
  }
}
```

The command collects from whichever MCP sources are available; missing sources produce `null` for their signal categories.

### R2: Check Phase Integration — Config-Gated (MUST)

The Check command playbook MUST include a new `Phase 4.7: Observability Scan` step (after Phase 4.5 PactGuard, before Phase 5 Verdict):
1. Read `check.observe.enabled` from `pactkit.yaml` — if `false` (default): **silently skip** (no Verdict row, no log)
2. If enabled: detect available MCP sources (Chrome DevTools, Playwright) — if none available: silently skip
3. If `mcp__chrome-devtools__*` tools are available: collect console errors, network failures
4. If Playwright MCP is available: take a post-test screenshot for visual verification
5. Format all signals via the observe protocol
6. Include in Verdict table: `Observability | PASS/WARN/FAIL | N console errors, M network failures`

Act and Done playbooks MUST NOT be modified.

### R3: Signal Severity Classification (MUST)

Collected signals MUST be classified by severity:
- **ERROR**: console errors, HTTP 5xx responses, uncaught exceptions → contributes to FAIL verdict
- **WARNING**: console warnings, HTTP 4xx responses (except 404), slow LCP (>2500ms) → contributes to WARN verdict
- **INFO**: HTTP 3xx redirects, successful requests, normal metrics → no verdict impact

### R4: Observation Report Format (MUST)

`pactkit observe --report` MUST generate a human-readable report:
```
## Observability Report (2026-03-31T10:00:00Z)

### Console (2 errors, 1 warning)
[E] app.js:42 — TypeError: Cannot read property 'x' of undefined
[E] api.js:15 — Unhandled promise rejection
[W] vendor.js:100 — Deprecation warning: ...

### Network (1 failure)
[E] POST /api/users → 500 Internal Server Error (230ms)

### Performance
LCP: 1200ms ✓ | FCP: 400ms ✓ | CLS: 0.05 ✓

### Verdict: WARN (2 console errors)
```

### R5: Configuration in pactkit.yaml (MUST)

The `check` section in `pactkit.yaml` MUST support a new `observe` sub-section:
```yaml
check:
  security_checklist: true          # existing
  security_scope_override: none     # existing
  pactguard:                        # STORY-slim-072
    enabled: false
  observe:                          # NEW
    enabled: false                  # default OFF
    sources: "auto"                 # auto | chrome-devtools | playwright | all
    max_console: 100                # cap collected console messages
    max_network: 200                # cap collected network requests
```

Defaults: `enabled: false`, `sources: "auto"`, `max_console: 100`, `max_network: 200`.

### R6: Playbook Template Variables (MUST)

New template variables for the Check playbook:
- `{OBSERVE_ENABLED}` — resolves to `true`/`false` from `check.observe.enabled`
- `{OBSERVE_SOURCES}` — resolves to configured sources value

### R7: Graceful Degradation (MUST)

When `check.observe.enabled: true` but MCP tools unavailable:
- `pactkit observe` prints `No observability sources available — skipping` and exits 0
- Check Phase 4.7 is silently skipped — no Verdict row

## Acceptance Criteria

### AC1: Silently Skips When Disabled (R2)

- **Given** `pactkit.yaml` has `check.observe.enabled: false` (or key absent)
- **When** `/project-check` runs
- **Then** Phase 4.7 is silently skipped — no log, no Verdict row for Observability

### AC2: Config Defaults Are OFF (R5)

- **Given** a fresh `pactkit.yaml` with no `check.observe` section
- **When** `load_config()` merges defaults
- **Then** `config["check"]["observe"]["enabled"]` is `False`

### AC3: Console Errors Collected (R1)

- **Given** `check.observe.enabled: true`, a running web app with `console.error("test failure")` in the browser
- **When** `pactkit observe` runs with Chrome DevTools MCP available
- **Then** output JSON includes `console_errors` array with the error message

### AC4: Network Failures Captured (R1)

- **Given** `check.observe.enabled: true`, a running web app where `POST /api/users` returns 500
- **When** `pactkit observe` runs
- **Then** output JSON includes `network_failures` with url, status 500, method POST

### AC5: Check Verdict Includes Observability When Enabled (R2, R6)

- **Given** `check.observe.enabled: true`, Check Phase 4 E2E passed, 3 console errors detected
- **When** Check Phase 4.7 runs
- **Then** Phase 5 Verdict includes `Observability | WARN | 3 console errors, 0 network failures`

### AC6: Severity Classification (R3)

- **Given** signals include: 1 console error, 1 HTTP 404, 1 HTTP 500
- **When** signals are classified
- **Then** console error → ERROR, HTTP 404 → excluded (unless configured), HTTP 500 → ERROR

### AC7: Silently Skips When No MCP Available (R7)

- **Given** `check.observe.enabled: true` but no Chrome DevTools MCP and no Playwright MCP available
- **When** `/project-check` runs Phase 4.7
- **Then** phase is silently skipped — no Verdict row

### AC8: Human-Readable Report (R4)

- **Given** 2 console errors and 1 network failure collected
- **When** `pactkit observe --report` runs
- **Then** output matches the structured report format with `[E]`/`[W]` prefixes and a Verdict line

## Target Call Chain

```
pactkit observe [--report] [--json]
  → cli.py: observe command dispatch
  → observe.py: run_observe(report=False, json_output=False)
    → _detect_sources() → ["chrome-devtools", "playwright"] or []
    → if "chrome-devtools" in sources:
      → mcp__chrome-devtools__list_console_messages → parse
      → mcp__chrome-devtools__list_network_requests → parse
      → mcp__chrome-devtools__performance_analyze_insight → parse (if available)
    → if "playwright" in sources:
      → mcp__playwright__browser_take_screenshot → save
    → _classify_signals(raw_signals) → classified with severity
    → _build_report(classified) → ObserveReport
    → format output (json or human-readable)

/project-check:
  → Phase 4.5: PactGuard [STORY-slim-072]
  → Phase 4.7: Observability Scan (NEW)
    → read config["check"]["observe"]["enabled"]
    → if false (default): silently skip → Phase 5
    → _detect_sources() → if empty: silently skip → Phase 5
    → run observability protocol
    → include in Verdict table
  → Phase 5: Verdict [existing, conditionally extended with Observability row]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_config.py` | TDD: tests for `check.observe` config parsing, defaults, validation | None | Low |
| 2 | `src/pactkit/config.py` | Add `observe` sub-section to `check` defaults, deep merge, validation | None | Low |
| 3 | `tests/unit/test_observe.py` | TDD: tests for signal classification, report formatting, graceful degradation | None | Low |
| 4 | `src/pactkit/observe.py` | Implement `_detect_sources()`, `_classify_signals()`, `_build_report()`, `run_observe()` | None | Medium |
| 5 | `src/pactkit/cli.py` | Add `observe` subcommand with `--report` and `--json` flags | Step 4 | Low |
| 6 | `src/pactkit/prompts/commands.py` | Add Phase 4.7 block to Check template (config-gated, silent skip) | Step 2 | Low |
| 7 | `src/pactkit/generators/deployer.py` | Add `{OBSERVE_*}` variables to `_render_prompt()` var_map | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | N/A | No user input — signals come from MCP tools |
| SEC-2 (Auth) | N/A | No auth changes |
| SEC-3 (Injection) | N/A | No command construction |
| SEC-4 (Secrets) | MUST | Console/network logs may contain tokens or credentials — observe report must redact Authorization headers and cookie values |
| SEC-5 (CORS) | N/A | CLI-only |
| SEC-6 (Path Traversal) | N/A | No file path handling from external input |
| SEC-7 (DoS) | SHOULD | Limit collected signals (max 100 console messages, max 200 network requests) to prevent unbounded output |
| SEC-8 (Dependencies) | N/A | No new dependencies; MCP tools are existing integrations |

## Out of Scope

- Log aggregation or persistence (observe is ephemeral — run, report, discard)
- Full OpenTelemetry integration (future: OTLP export for production monitoring)
- Server-side log collection (only browser-side via MCP)
- Automated remediation based on observability signals
- Custom MCP source plugins (only Chrome DevTools and Playwright in v3.0.0)
- Act/Done phase integration (all observe logic is in Check only)
- Activation friction reduction (doctor hints, auto-enable) — deferred to dogfood validation
