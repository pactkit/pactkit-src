# STORY-slim-107: Integrate tech debt prevention patterns into framework rules

| Field | Value |
|-------|-------|
| ID | STORY-slim-107 |
| Status | Done |
| Priority | P1 |
| Release | 2.12.0 |

## Background

A tech debt cleanup across the pactsearch project (BUG-172~191, STORY-182~209) yielded 12 recurring anti-patterns. These were captured in a personal rules file (`13-tech-debt-patterns.md`) but are not yet available to PactKit framework users. The valuable, language-agnostic patterns should be integrated into the existing deployed rule modules (`architecture` and `solution`) so all PactKit users benefit from these lessons.

**Source material**: `~/.claude/rules/13-tech-debt-patterns.md` (12 rules derived from real tech debt specs)

**Integration targets** (no new rule files — enrich existing ones):
- `architecture` module (`08-architecture-principles.md`): expand §1 DRY, expand §6 Security, add §10–§13
- `solution` module (`12-solution-design.md`): add String→Enum pattern to Implementation Constraints

## Requirements

### R1: Expand Architecture §1 DRY with Dual-Write Prevention (MUST)

Add a "No Dual-Write" sub-section to §1 Single Source of Truth (DRY) with:
- Anti-pattern table (Memory+DB, Cache+Source, Frontend+Backend enums, File+DB)
- Fix pattern (choose ONE truth source; others become read-cache or projection)
- Keep language-agnostic (no owlready2/rdflib references)

### R2: Expand Architecture §6 Security with Deny-by-Default, Input Validation, and Timing Consistency (MUST)

Extend §6 Defense-in-Depth with three new sub-sections:
- **Deny-by-Default**: Sensitive endpoints MUST require auth by default; empty config = denied
- **Input Validation**: User input entering URLs, commands, SQL, file paths MUST be validated/escaped (table by destination type)
- **Timing Consistency**: Security-sensitive branches MUST have consistent timing to prevent side-channel attacks

### R3: Add Architecture §10 Code Enforces, Prompt Instructs (MUST)

New principle with litmus test: "If the LLM ignores the prompt instruction, does the constraint still hold?" Includes anti-pattern table (SQL limit, input length, output format, date freshness) and LLM≠Calculator decision matrix.

### R4: Add Architecture §11 Concurrency & Async Safety (SHOULD)

New principle covering:
- Fire-and-forget tasks MUST NOT silently fail (error visibility, backpressure, shutdown awareness)
- Request-scoped state (ContextVar or equivalent) MUST be cleaned up in finally blocks
- Shared mutable state MUST be protected (lock, semaphore lazy-init)

### R5: Add Architecture §12 Cache Lifecycle (SHOULD)

New principle: every cache MUST be registered in a central invalidation function. Write operations MUST declare which caches they affect.

### R6: Add Architecture §13 Dead Code Hygiene (SHOULD)

New principle: unused functions, empty middleware, unwired components MUST be deleted or activated. Categories table (dead function, empty middleware, unwired component, commented code).

### R7: Add String→Enum Pattern to Solution Design (SHOULD)

In `solution` module under Implementation Constraints (after No Magic Values), add a `String Literal → Enum` sub-section:
- Rule: any string value appearing in 3+ places SHOULD be promoted to a typed enum
- Language-agnostic pattern (Python `str, Enum`; TypeScript `as const`; etc.)
- Migration checklist (define enum, replace literals, verify with grep)

## Acceptance Criteria

### AC1: Architecture module deploys with new principles (R1, R2, R3, R4, R5, R6)

- **Given** PactKit v2.12.0 is deployed via `pactkit deploy`
- **When** the `08-architecture-principles.md` file is generated
- **Then** it contains §1 with dual-write sub-section, §6 with 3 security sub-sections, §10 Code Enforces, §11 Concurrency Safety, §12 Cache Lifecycle, §13 Dead Code Hygiene

### AC2: Solution module deploys with String→Enum pattern (R7)

- **Given** PactKit v2.12.0 is deployed via `pactkit deploy`
- **When** the `12-solution-design.md` file is generated
- **Then** it contains a "String Literal → Enum" sub-section under Implementation Constraints

### AC3: All rules are language-agnostic (R1-R7)

- **Given** the new rule content in `rules.py`
- **When** reviewed for project-specific references
- **Then** no pactsearch-specific terms (owlready2, rdflib, pactsearch, BUG-172, STORY-182, etc.) appear — only generic patterns

### AC4: Existing tests pass (R1-R7)

- **Given** the modified `rules.py`
- **When** `pytest tests/ -v` is run
- **Then** all existing tests pass with 0 failures

### AC5: RULES_MANAGED_PREFIXES unchanged (R1-R7)

- **Given** no new rule files are created
- **When** `RULES_MANAGED_PREFIXES` is inspected
- **Then** it is identical to the pre-change value (no new prefix added)

## Target Call Chain

```
rules.py:RULES_MODULES["architecture"]  → deployer._deploy_rules() → atomic_write(08-architecture-principles.md)
rules.py:RULES_MODULES["solution"]      → deployer._deploy_rules() → atomic_write(12-solution-design.md)
```
No new modules, no new files, no new keys — only content changes within existing string values.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Expand `architecture` §1 with dual-write sub-section | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | Expand `architecture` §6 with deny-by-default, input validation, timing consistency | Step 1 | Low |
| 3 | `src/pactkit/prompts/rules.py` | Add `architecture` §10 Code Enforces / LLM≠Calculator | Step 2 | Low |
| 4 | `src/pactkit/prompts/rules.py` | Add `architecture` §11 Concurrency & Async Safety | Step 3 | Low |
| 5 | `src/pactkit/prompts/rules.py` | Add `architecture` §12 Cache Lifecycle | Step 4 | Low |
| 6 | `src/pactkit/prompts/rules.py` | Add `architecture` §13 Dead Code Hygiene | Step 5 | Low |
| 7 | `src/pactkit/prompts/rules.py` | Add String→Enum pattern to `solution` Implementation Constraints | None | Low |
| 8 | `tests/` | Run full test suite, verify 0 failures | Steps 1-7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt content only, no credentials |
| SEC-2 | N/A | No file path handling changes |
| SEC-3 | N/A | No user input processing |
| SEC-4 | N/A | No network calls |
| SEC-5 | N/A | No shell commands |
| SEC-6 | N/A | No config file writes |
| SEC-7 | N/A | No dependency changes |
| SEC-8 | N/A | No API endpoints |

## Out of Scope

- Creating new rule files (no `13-*.md` or `14-*.md` in PactKit framework)
- `pactkit audit` CLI integration (future story)
- Modifying `RULES_MANAGED_PREFIXES`, `RULES_FILES`, or `COMMAND_RULES_MAP`
- P.A.C.T. philosophy rules (personal, not framework-level)
- Project-specific examples (pactsearch owlready2, rdflib, etc.)
