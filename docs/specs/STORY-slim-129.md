# STORY-slim-129: Engineering Concerns Guide Expansion — 6 Additional NFR Guides

| Field | Value |
|-------|-------|
| ID | STORY-slim-129 |
| Status | Done |
| Priority | P1 |
| Release | 2.15.1 |

## Background

STORY-slim-128 established the Engineering Concerns guide system with 13 on-demand guides covering concurrency, async, configuration, observability, module design, database, caching, API integration, event-driven, resilience, memory management, code-review-first, and component-reuse.

Analysis of common LLM-generated code weaknesses identified 6 additional high-frequency gaps:
1. **Error Recovery & Retry** — LLM try/catch blocks almost always just `log + return None`, missing retry with backoff, idempotency, partial failure handling
2. **Data Consistency** — multi-table/multi-service writes without transaction strategy, no idempotency key, no compensation
3. **Backwards Compatibility** — LLM defaults to breaking changes for API/schema modifications
4. **Performance Anti-patterns** — N+1 queries, unbounded list APIs, missing indices, hot-path serialization
5. **Graceful Shutdown** — no SIGTERM handler, no in-flight request drain, no resource cleanup ordering
6. **Testing Strategy** — LLM writes tests without considering boundary testing, mock vs real, or test isolation

## Requirements

### R1: Six New Guide Files (MUST)

Add 6 new guide files to `GUIDES_FILES` in `src/pactkit/prompts/guides.py`:
- `error-recovery.md` — retry strategies, backoff, idempotency, partial failure
- `data-consistency.md` — distributed transactions, idempotency keys, optimistic/pessimistic locking, Saga
- `backwards-compatibility.md` — API versioning, non-breaking DB migrations, protocol evolution
- `performance-antipatterns.md` — N+1 queries, unbounded queries, missing indexes, hot-path costs
- `graceful-shutdown.md` — SIGTERM handling, request drain, resource cleanup order
- `testing-strategy.md` — boundary testing, mock vs real, test isolation, deterministic tests

Each guide MUST follow existing format: Decision Table + MUST + NEVER + Template, ≤ 50 lines.

### R2: Trigger Index Update (MUST)

Add 6 new rows to the keyword→concern table in `RULES_MODULES["engineering"]` in `src/pactkit/prompts/rules.py`:
- error-recovery: retry/重试/backoff/幂等/idempoten/partial failure
- data-consistency: 一致性/consistency/saga/补偿/idempotency key/分布式事务
- backwards-compatibility: 兼容/backward/breaking change/deprecat/migration/版本
- performance-antipatterns: N+1/unbounded/分页/pagina/index/索引/热路径/hot path
- graceful-shutdown: shutdown/优雅关闭/SIGTERM/drain/信号处理
- testing-strategy: 测试策略/test strategy/mock/stub/boundary/隔离/isolation

### R3: Guide Loading Table Update (MUST)

Add 6 new rows to the Act Phase Guide Loading Table in the same `engineering` module content, mapping concern→guide file path.

### R4: Pre-existing Test Update (MUST)

Update hardcoded counts in tests:
- `test_story_slim128_engineering_concerns.py`: 13→19 guide count
- `test_story_slim026.py`: plan prompt char baseline if exceeded
- `test_story063_prompt_slimming.py`: BASELINE_TOTAL_CHARS if exceeded
- Trigger index "NEVER load all 13" → "NEVER load all 19"

### R5: Token Budget Control (SHOULD)

Total trigger index growth SHOULD be ≤ 8 lines (6 keyword rows + 6 guide path rows = 12 table rows, but table rows are short). The trigger index must remain under ~60 lines total.

### R6: Guide Loading Cap (MUST)

Maintain the "MUST load only 1-3 relevant guides" instruction. Do NOT increase the cap — more guides available does not mean more should be loaded simultaneously.

## Acceptance Criteria

### AC1: Guide Files Registered (R1)

- **Given** `GUIDES_FILES` dict in `src/pactkit/prompts/guides.py`
- **When** the module is loaded
- **Then** it contains exactly 19 entries (13 original + 6 new), each ≤ 50 lines with MUST and NEVER sections

### AC2: Trigger Index Extended (R2, R3)

- **Given** `RULES_MODULES["engineering"]` in rules.py
- **When** the content is inspected
- **Then** the keyword table has 19 rows and the guide loading table has 19 rows

### AC3: Deployment Creates 19 Guide Files (R1)

- **Given** `_deploy_guides()` is called
- **When** deployment completes
- **Then** 19 `.md` files exist in `skills/_rules/guides/` directory

### AC4: Guide Loading Cap Unchanged (R6)

- **Given** trigger index content
- **When** inspected for loading instruction
- **Then** still says "MUST load only 1-3 relevant guides" (not 4+)

### AC5: All Tests Pass (R4)

- **Given** updated test expectations (19 guides)
- **When** full test suite runs
- **Then** all tests pass including pre-existing count assertions

## Target Call Chain

```
guides.py::GUIDES_FILES (add 6 entries)
  → rules.py::RULES_MODULES["engineering"] (extend keyword table + guide table)
    → deployer.py::_deploy_guides() (already handles any GUIDES_FILES count)
      → tests/ (update count assertions 13→19)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/guides.py` | Add 6 new guide entries to GUIDES_FILES | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | Add 6 keyword rows + 6 guide loading rows to engineering module | Step 1 | Low |
| 3 | `tests/unit/test_story_slim128_engineering_concerns.py` | Update count 13→19, update EXPECTED_GUIDES set | Steps 1-2 | Low |
| 4 | Other test files | Update baselines if char counts exceeded | Steps 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | docs/tests only |
| SEC-2 Auth/AuthZ | N/A | docs/tests only |
| SEC-3 Data Exposure | N/A | docs/tests only |
| SEC-4 Cryptography | N/A | docs/tests only |
| SEC-5 Error Handling | N/A | docs/tests only |
| SEC-6 Dependencies | N/A | docs/tests only |
| SEC-7 Logging | N/A | docs/tests only |
| SEC-8 Config/Secrets | N/A | docs/tests only |

## Out of Scope

- No changes to deployer logic (already handles dynamic GUIDES_FILES count)
- No changes to command prompts (plan/act phases already reference the trigger index)
- No new RULES_ONDEMAND_FILES entry needed (engineering key already exists)
- No config.py changes (VALID_RULES already includes 07-engineering-concerns)
